<?php

namespace App\Services;

use App\Exceptions\InnBucksException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

class InnBucks
{
    private const TOKEN_CACHE_KEY = 'innbucks.access_token';

    public ?string $lastTraceId = null;

    // ---- authentication -------------------------------------------------

    /** A cached bearer token; logs in when there is none (or $fresh is true). */
    public function token(bool $fresh = false): string
    {
        if ($fresh) {
            Cache::forget(self::TOKEN_CACHE_KEY);
        }

        return Cache::remember(self::TOKEN_CACHE_KEY, config('services.innbucks.token_ttl', 840), function () {
            $response = $this->http()->post('/auth/third-party', [
                'username' => config('services.innbucks.username'),
                'password' => config('services.innbucks.password'),
            ]);
            $body = $this->decode($response);

            if (! self::ok($body) || empty($body['accessToken'])) {
                throw new InnBucksException('InnBucks login failed: '.self::message($body), $body, $this->lastTraceId, $response->status());
            }

            return $body['accessToken'];
        });
    }

    // ---- codes: payments and withdrawals --------------------------------

    /** Generate a PAYMENT or WITHDRAWAL code. $amountCents: 450 = 4.50. */
    public function generateCode(int $amountCents, string $currency, string $reference,
                                 string $narration, string $type = 'PAYMENT'): array
    {
        return $this->send('POST', '/api/code/generate', [
            'reference' => $reference,
            'narration' => $narration,
            'currency'  => self::currency($currency),
            'amount'    => self::cents($amountCents),
            'type'      => in_array($type, ['PAYMENT', 'WITHDRAWAL'], true) ? $type
                           : throw new \InvalidArgumentException('type must be PAYMENT or WITHDRAWAL'),
        ]);
    }

    /** Current status of a code. Call at most once every 30 seconds per code. */
    public function inquireCode(string $code, ?string $reference = null): array
    {
        return $this->send('POST', '/api/code/inquiry', array_filter([
            'reference' => $reference,
            'code'      => $code,
        ], fn ($v) => $v !== null));
    }

    // ---- agent services -------------------------------------------------

    public function linkedAccount(string $msisdn, string $currency = 'USD'): array
    {
        return $this->send('GET', '/api/v1/account/msisdn/'.rawurlencode($msisdn).'/details?currency='.self::currency($currency));
    }

    public function deposit(string $destinationAccount, int $amountCents, string $currency,
                            string $reference, string $narration, ?string $type = null): array
    {
        return $this->send('POST', '/api/transaction/deposit', array_filter([
            'reference'          => $reference,
            'currency'           => self::currency($currency),
            'amount'             => self::cents($amountCents),
            'narration'          => $narration,
            'destinationAccount' => $destinationAccount,
            'type'               => $type,
        ], fn ($v) => $v !== null));
    }

    public function depositInquiry(string $accountNumber, string $originalReference, string $inquiryReference): array
    {
        return $this->send('POST', '/bank/api/transaction/inquiry', [
            'accountNumber'                => $accountNumber,
            'participantReference'         => $inquiryReference,
            'originalParticipantReference' => $originalReference,
        ]);
    }

    /** Reverse a DEPOSIT. Amount and account must match the original exactly. */
    public function reverseDeposit(string $destinationAccount, int $amountCents, string $currency,
                                   string $originalReference, string $reversalReference): array
    {
        return $this->send('POST', '/api/transaction/reversal/v2', [
            'amount'                       => self::cents($amountCents),
            'currency'                     => self::currency($currency),
            'type'                         => 'CREDIT',
            'destinationAccount'           => $destinationAccount,
            'participantReference'         => $reversalReference,
            'originalParticipantReference' => $originalReference,
        ]);
    }

    /** Credit a cash customer's change to their wallet: US$5.00 (500 cents) or less. */
    public function bankChange(string $msisdn, int $amountCents, string $currency,
                               string $reference, string $narration): array
    {
        if (strtoupper($currency) === 'USD' && $amountCents > 500) {
            throw new \InvalidArgumentException('Bank change is limited to 500 cents (US$5.00).');
        }

        return $this->send('POST', '/api/transaction/bankChange', [
            'reference'         => $reference,
            'currency'          => self::currency($currency),
            'amount'            => self::cents($amountCents),
            'narration'         => $narration,
            'destinationMsisdn' => $msisdn,
        ]);
    }

    public function utilityPayment(string $provider, string $product, string $destinationAccount,
                                   int $amountCents, string $currency, string $reference,
                                   string $narration = '', array $additionalData = []): array
    {
        return $this->send('POST', '/api/utility/provider/payment', [
            'provider'           => $provider,
            'providerProduct'    => $product,
            'amount'             => self::cents($amountCents),
            'currency'           => self::currency($currency),
            'reference'          => $reference,
            'narration'          => $narration,
            'destinationAccount' => $destinationAccount,
            'additionalData'     => (object) $additionalData,
        ]);
    }

    /** $start / $end as 'Y-m-d H:i:s', within one calendar month. */
    public function statement(string $accountNumber, string $currency, string $start, string $end): array
    {
        return $this->send('POST', '/api/account/fullStatement', [
            'accountNumber' => $accountNumber,
            'currency'      => self::currency($currency),
            'startDateTime' => $start,
            'endDateTime'   => $end,
        ]);
    }

    // ---- helpers --------------------------------------------------------

    public static function ok(array $body): bool
    {
        return in_array($body['responseCode'] ?? null, ['00', '000'], true);
    }

    public static function message(array $body): string
    {
        return (string) ($body['responseMsg'] ?? $body['responseDescription'] ?? 'no message');
    }

    /** new | claimed | paid | expired | timed_out | null */
    public static function codeStatus(array $body): ?string
    {
        $s = strtolower(preg_replace('/[\s_-]+/', '', (string) ($body['status'] ?? '')));

        return ['new' => 'new', 'claimed' => 'claimed', 'paid' => 'paid',
                'expired' => 'expired', 'timedout' => 'timed_out'][$s] ?? null;
    }

    public static function isPaid(array $body): bool
    {
        return self::ok($body) && in_array(self::codeStatus($body), ['claimed', 'paid'], true);
    }

    public static function isFinal(array $body): bool
    {
        return self::ok($body) && in_array(self::codeStatus($body), ['claimed', 'paid', 'expired', 'timed_out'], true);
    }

    public static function deepLink(string $code): string
    {
        $scheme = config('services.innbucks.environment') === 'production'
            ? 'com.innbucks.customer'
            : 'zw.co.innbucksnova.test';

        return $scheme.'://purchase?paymentToken='.rawurlencode($code);
    }

    /** A data: URI for an <img> tag, whether or not qrCode already carries the prefix. */
    public static function qrDataUri(array $body): ?string
    {
        $qr = $body['qrCode'] ?? null;

        return $qr === null ? null : (str_starts_with($qr, 'data:') ? $qr : 'data:image/png;base64,'.$qr);
    }

    private static function cents(int $amount): int
    {
        if ($amount <= 0) {
            throw new \InvalidArgumentException('Amounts are positive integers in cents: 450 = 4.50.');
        }

        return $amount;
    }

    private static function currency(string $currency): string
    {
        $currency = strtoupper($currency);

        return in_array($currency, ['USD', 'ZWG'], true) ? $currency
            : throw new \InvalidArgumentException('currency must be USD or ZWG');
    }

    private function http(): PendingRequest
    {
        return Http::baseUrl(rtrim(config('services.innbucks.base_url'), '/'))
            ->withHeaders(['X-Api-Key' => config('services.innbucks.api_key')])
            ->acceptJson()
            ->asJson()
            ->timeout(30);
    }

    private function send(string $method, string $path, array $body = []): array
    {
        $call = fn (string $token) => $this->http()->withToken($token)
            ->send($method, $path, $method === 'GET' ? [] : ['json' => $body]);

        $response = $call($this->token());
        if ($response->status() === 401) {         // token expired: log in again, retry once
            $response = $call($this->token(fresh: true));
        }

        $decoded = $this->decode($response);
        if ($response->failed()) {
            throw new InnBucksException("InnBucks HTTP {$response->status()}: ".self::message($decoded),
                $decoded, $this->lastTraceId, $response->status());
        }

        return $decoded;
    }

    private function decode(Response $response): array
    {
        $this->lastTraceId = $response->header('X-Trace-Id') ?: null;

        return $response->json() ?? [];
    }
}
