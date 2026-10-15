# Kotlin integration (Android app + JVM backend)

## Contents
- Architecture: the key never ships in the app
- Dependencies
- Shared API models (kotlinx.serialization)
- Mapping a choice answer onto your enum
- Backend: Retrofit client for Jev on OpenRouter with retry
- Logging: mask the Authorization header
- Backend: a use-case function that builds questions
- Android: calling your backend and gating on confidence
- Alternative: community SDKs and other routes
- Testing

The samples use Retrofit, OkHttp and kotlinx.serialization. Rename packages and types to
fit your project.

## Architecture: the key never ships in the app

```
Android app ──(your auth)──▶ your backend ──(OPENROUTER_API_KEY)──▶ openrouter.ai/api/alpha/decisions
```

- An API key inside an APK/AAB can be extracted with standard tools, obfuscation or not.
  Keep it in the backend's secret store. An OpenRouter key can call every model on the
  account, so a leak costs more than Jev usage: set a credit limit on the key.
- Expose **use-case endpoints** from the backend (e.g. `POST /decisions/ticket-triage`),
  not a generic "forward any question" endpoint. The backend owns the questions, so a
  client can't turn your key into a free general-purpose API, and question wording
  changes don't need an app release.
- Only send the fields the questions need. Mask phone numbers, names and addresses unless
  the decision needs them.
- OpenRouter's Jev route caps state plus all questions combined at 32k tokens (TypeSafe
  direct is 64k total, 32k for state plus the longest question) — see `references/api.md`.

## Dependencies

```kotlin
// build.gradle.kts (backend and/or shared module)
plugins { kotlin("plugin.serialization") version "<your Kotlin version>" }

dependencies {
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
}
```
Check for newer versions before adding; these are known-good baselines.

## Shared API models (kotlinx.serialization)

```kotlin
// JevModels.kt: request and answer models for Jev decisions via OpenRouter.
package com.example.jev

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

/** `type` is the class discriminator for both questions and answers. */
val jevJson = Json {
    classDiscriminator = "type"
    ignoreUnknownKeys = true   // new API fields must not break old clients
    explicitNulls = false      // omit optional noul criteria when absent
    encodeDefaults = true
}

@Serializable
data class SystemOneRequest(
    val model: String,
    val state: JsonElement,
    val questions: Map<String, JevQuestion>,
)

@Serializable
sealed interface JevQuestion {
    val instructions: String

    @Serializable @SerialName("noul")
    data class Noul(
        override val instructions: String,
        val criteria: NoulCriteria? = null,
    ) : JevQuestion

    /** Option key to description. Always describe options and include a "none" option. */
    @Serializable @SerialName("choice")
    data class Choice(
        override val instructions: String,
        val criteria: Map<String, String>,
    ) : JevQuestion

    /** Ordered levels, lowest first, 2 to 10 entries. */
    @Serializable @SerialName("score")
    data class Score(
        override val instructions: String,
        val criteria: List<String>,
    ) : JevQuestion
}

@Serializable
data class NoulCriteria(
    @SerialName("true") val meaningOfYes: String,
    @SerialName("false") val meaningOfNo: String,
)

@Serializable
data class SystemOneResponse(
    val model: String,
    val answers: Map<String, JevAnswer>,
    val usage: JevUsage,
)

@Serializable
sealed interface JevAnswer {
    @Serializable @SerialName("noul")
    data class Noul(val noul: Double) : JevAnswer

    @Serializable @SerialName("choice")
    data class Choice(
        val choice: String,
        val probabilities: Map<String, Double>,
        val confidence: Double,
    ) : JevAnswer

    @Serializable @SerialName("score")
    data class Score(
        val score: Double,
        val probabilities: Map<String, Double>,
        val legend: Map<String, String>,
        val confidence: Double,
    ) : JevAnswer
}

@Serializable
data class JevUsage(
    @SerialName("input_tokens") val inputTokens: Int,
    @SerialName("output_tokens") val outputTokens: Int,
    val cost: Double? = null,   // USD, present on OpenRouter; log it for real per-call cost
)

/** Typed accessors so call sites fail loudly if a question id or type is wrong. */
fun SystemOneResponse.noulOf(questionId: String): Double =
    (answers[questionId] as? JevAnswer.Noul)?.noul
        ?: error("Missing noul answer for '$questionId'")

fun SystemOneResponse.choiceOf(questionId: String): JevAnswer.Choice =
    answers[questionId] as? JevAnswer.Choice
        ?: error("Missing choice answer for '$questionId'")

fun SystemOneResponse.scoreOf(questionId: String): JevAnswer.Score =
    answers[questionId] as? JevAnswer.Score
        ?: error("Missing score answer for '$questionId'")
```

## Mapping a choice answer onto your enum

A choice answer's `choice` field is a plain `String`. Compare it once, not at every call
site: map it onto your own enum with a fallback for anything unrecognised (a new option
added on the backend, or Jev's own `none`).

```kotlin
/** Maps a Jev choice answer onto [T] by [key] (case-insensitive), or [fallback] if nothing matches. */
inline fun <reified T : Enum<T>> enumFromChoice(answer: JevAnswer.Choice, key: (T) -> String, fallback: T): T =
    enumValues<T>().firstOrNull { key(it).equals(answer.choice, ignoreCase = true) } ?: fallback

enum class SupportDepartment(val jevKey: String) {
    PAYMENTS("payments"), TRIP_ISSUE("trip_issue"), ACCOUNT("account"),
    SAFETY("safety"), NONE("none"), UNKNOWN("unrecognised");
}

val department = enumFromChoice(response.choiceOf("department"), SupportDepartment::jevKey, fallback = SupportDepartment.UNKNOWN)
```

## Backend: Retrofit client for Jev on OpenRouter with retry

```kotlin
// JevDecisionService.kt: Retrofit service and HTTP setup for OpenRouter's decisions endpoint.
package com.example.jev

import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

const val JEV_MODEL_SLUG = "typesafe/jev-1.13"

interface JevDecisionService {
    /** `alpha` path: if it starts returning 404, check OpenRouter's Jev page for the new one. */
    @POST("alpha/decisions")
    suspend fun requestJevDecisions(@Body request: SystemOneRequest): SystemOneResponse
}

/** Adds the OpenRouter key and optional ranking headers. Server-side only, never in the app. */
class OpenRouterAuthInterceptor(
    private val apiKey: String,
    private val appUrl: String? = null,
    private val appName: String? = null,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response =
        chain.request().newBuilder().apply {
            header("Authorization", "Bearer $apiKey")
            appUrl?.let { header("HTTP-Referer", it) }
            appName?.let { header("X-Title", it) }
        }.build().let(chain::proceed)
}

/** Retries 429/529/5xx with exponential backoff, honouring retry-after. 401/402 are not retried. */
class JevRetryInterceptor(private val maxAttempts: Int = 4) : Interceptor {
    private val retryableStatuses = setOf(429, 500, 502, 503, 504, 529)

    override fun intercept(chain: Interceptor.Chain): Response {
        var attempt = 1
        var response = chain.proceed(chain.request())
        while (response.code in retryableStatuses && attempt < maxAttempts) {
            val waitMillis = response.header("retry-after")?.toLongOrNull()?.times(1_000)
                ?: (1_000L shl (attempt - 1))
            response.close()
            Thread.sleep(waitMillis.coerceAtMost(30_000))
            attempt++
            response = chain.proceed(chain.request())
        }
        return response
    }
}

fun createJevDecisionService(
    openRouterApiKey: String,
    appUrl: String? = null,
    appName: String? = null,
): JevDecisionService {
    val httpClient = OkHttpClient.Builder().apply {
        addInterceptor(OpenRouterAuthInterceptor(openRouterApiKey, appUrl, appName))
        addInterceptor(JevRetryInterceptor())
        connectTimeout(10, TimeUnit.SECONDS)
        readTimeout(30, TimeUnit.SECONDS)
    }.build()

    return Retrofit.Builder()
        .baseUrl("https://openrouter.ai/api/")
        .client(httpClient)
        .addConverterFactory(jevJson.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(JevDecisionService::class.java)
}
```

Read the key from the backend's secret store (e.g. env `OPENROUTER_API_KEY`). Keep the
model slug in config so a version move is a config change, and log `response.model`.
A 402 means the OpenRouter account is out of credit: alert on it rather than retrying.
Read `response.usage.cost` for the real per-call cost instead of estimating from the
list price — OpenRouter includes it on every response.

## Logging: mask the Authorization header

Never let the OpenRouter key reach logs. OkHttp's own logging interceptor supports
redacting a header by name:

```kotlin
val loggingInterceptor = HttpLoggingInterceptor().apply {
    level = HttpLoggingInterceptor.Level.BASIC
    redactHeader("Authorization")
}
```

Add it to the same `OkHttpClient.Builder` as `OpenRouterAuthInterceptor` and
`JevRetryInterceptor` above. Use `Level.BASIC` in production; `BODY` would also log
`state`, which may contain user content.

## Backend: a use-case function that builds questions

Example: triaging a rider/driver support message. All questions go in **one** request.

```kotlin
// TicketTriageDecider.kt: support ticket triage decision built on Jev.
package com.example.support

import com.example.jev.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

@Serializable
data class TicketTriageDecision(
    val department: String,
    val departmentPMax: Double,
    val urgencyProbability: Double,
    val frustrationScore: Double,
    val needsHumanReview: Boolean,
    val modelVersion: String,
)

class TicketTriageDecider(
    private val jevDecisionService: JevDecisionService,
    private val modelSlug: String = JEV_MODEL_SLUG,
) {
    suspend fun decideTicketTriage(message: String, userRole: String): TicketTriageDecision {
        val request = SystemOneRequest(
            model = modelSlug,
            state = buildJsonObject {
                put("message", message)
                put("user_role", userRole)
            },
            questions = mapOf(
                "department" to JevQuestion.Choice(
                    instructions = "Which team should handle `message`?",
                    criteria = mapOf(
                        "payments" to "Charges, refunds, wallet, payouts",
                        "trip_issue" to "Problems during a ride or delivery: route, delay, item damage",
                        "account" to "Login, verification, profile, ban appeals",
                        "safety" to "Harassment, accidents, threats, unsafe driving",
                        "none" to "No listed team fits",
                    ),
                ),
                "is_urgent" to JevQuestion.Noul(
                    instructions = "Does `message` describe something that needs action within the hour?",
                    criteria = NoulCriteria(
                        meaningOfYes = "Ongoing trip, safety risk, or money actively being lost",
                        meaningOfNo = "Past event or general question with no time pressure",
                    ),
                ),
                "frustration" to JevQuestion.Score(
                    instructions = "How frustrated is the writer of `message`?",
                    criteria = listOf(
                        "Calm, stating facts",
                        "Annoyed but polite",
                        "Angry, strong language or threats to leave",
                    ),
                ),
            ),
        )

        return jevDecisionService.requestJevDecisions(request).run {
            val department = choiceOf("department")
            val departmentPMax = department.probabilities.values.maxOrNull() ?: 0.0
            val urgency = noulOf("is_urgent")
            TicketTriageDecision(
                department = department.choice,
                departmentPMax = departmentPMax,
                urgencyProbability = urgency,
                frustrationScore = scoreOf("frustration").score,
                needsHumanReview = departmentPMax < 0.5 ||
                    department.choice in setOf("safety", "none") ||
                    (urgency > 0.2 && urgency < 0.8),
                modelVersion = model,
            )
        }
    }
}
```

Note the safety rule: the `safety` category always goes to a human, whatever the
confidence. Policy lives in code, not in the model.

## Android: calling your backend and gating on confidence

The app reuses `TicketTriageDecision` from a module shared with the backend (or keeps an
identical copy).

```kotlin
// SupportDecisionService.kt (Android app): your backend's support-decision endpoints.
package com.example.app.support

import com.example.support.TicketTriageDecision
import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.POST

interface SupportDecisionService {
    @POST("decisions/ticket-triage")
    suspend fun requestTicketTriageDecision(
        @Body body: TicketTriageRequestBody,
    ): TicketTriageDecision
}

@Serializable
data class TicketTriageRequestBody(val message: String)
```

```kotlin
// SupportDecisionRepository.kt (Android app): never throws into the UI.
package com.example.app.support

import com.example.support.TicketTriageDecision
import retrofit2.HttpException
import java.io.IOException

class SupportDecisionRepository(
    private val supportDecisionService: SupportDecisionService,
) {
    suspend fun fetchTicketTriageDecision(message: String): TicketTriageResult =
        try {
            TicketTriageResult.Decided(
                supportDecisionService.requestTicketTriageDecision(TicketTriageRequestBody(message))
            )
        } catch (exception: HttpException) {
            TicketTriageResult.Unavailable(reason = "HTTP ${exception.code()}")
        } catch (exception: IOException) {
            TicketTriageResult.Unavailable(reason = "Network error")
        }
}

sealed interface TicketTriageResult {
    data class Decided(val decision: TicketTriageDecision) : TicketTriageResult
    data class Unavailable(val reason: String) : TicketTriageResult
}
```

In the UI, always keep a manual path. Unavailable or low-confidence decisions fall back
to the normal category picker rather than blocking the user (`isVisible` is from
`androidx.core.view`):

```kotlin
when (result) {
    is TicketTriageResult.Decided -> binding.apply {
        tvSuggestedDepartment.text = result.decision.department
        groupSuggestedDepartment.isVisible = !result.decision.needsHumanReview
        spinnerDepartmentPicker.isVisible = result.decision.needsHumanReview
    }
    is TicketTriageResult.Unavailable -> binding.apply {
        groupSuggestedDepartment.isVisible = false
        spinnerDepartmentPicker.isVisible = true
    }
}
```

## Alternative: community SDKs and other routes

TypeSafe's own SDKs are built for its direct API (`api.typesafe.ai/v1/systemone`), but
OpenRouter also proxies that exact path at `openrouter.ai/api/v1/systemone` so those SDKs
can run on an OpenRouter key by changing only the base URL — same request/response shape
as the `alpha/decisions` route this file uses. Confirm it against a real key before relying
on it; it isn't what this file's Retrofit client does.

An unofficial Kotlin/Android SDK, `typesafe-sdk-kotlin` (github.com/ufec/typesafe-sdk-kotlin,
via JitPack, targets `minSdk` 29, needs a JDK 17 toolchain), ports `@typesafe-ai/sdk` with
`noul()`/`choice()`/`score()` builders and a configurable `baseUrl`. It targets TypeSafe
direct and takes the API key as an explicit constructor argument (there's no `process.env`
on Android to read it from). Pointing its `baseUrl` at OpenRouter's passthrough above is
plausible but unverified — check its response parsing against a real OpenRouter call first.
Verify any other community SDK's facts yourself before repeating them; these projects and
their APIs change fast.

## Testing

- Unit-test the decider with a fake `JevDecisionService` returning canned
  `SystemOneResponse` objects that cover: clear winner, spread-out low confidence,
  `none` chosen, noul near 0.5. Assert the gating logic, not the model.
- Keep a small labelled set (30–100 real, anonymised messages) and re-run it when you
  change question wording or move to a new model version. Compare accuracy and how many
  cases land in human review.
- Deserialisation test: feed the exact JSON example from `references/api.md` through
  `jevJson.decodeFromString<SystemOneResponse>()` to catch model/field drift.
