module Partas.Retry

open System

/// <summary>How a failed operation is retried.</summary>
type RetryPolicy =
    { Attempts: int
      Delay: TimeSpan
      Backoff: float }

/// <summary>Builds a <c>RetryPolicy</c> one setting at a time.</summary>
type RetryPolicyBuilder() =
    let mutable policy = { Attempts = 3; Delay = TimeSpan.FromSeconds 1.0; Backoff = 1.0 }

    /// <summary>Waits the given number of milliseconds before the first retry.</summary>
    /// <remarks>
    /// The delay is the wait before the first retry only. Later waits multiply it by the backoff
    /// factor, so with a factor of 2.0 and 100 ms the waits are 100, 200, 400 ms.
    /// </remarks>
    member this.Delay(milliseconds: int) =
        policy <- { policy with Delay = TimeSpan.FromMilliseconds(float milliseconds) }
        this

    /// <summary>Waits the given time span before the first retry.</summary>
    /// <remarks>
    /// The delay is the wait before the first retry only. Later waits multiply it by the backoff
    /// factor, so with a factor of 2.0 and 100 ms the waits are 100, 200, 400 ms.
    /// </remarks>
    member this.Delay(delay: TimeSpan) =
        policy <- { policy with Delay = delay }
        this

    /// <summary>Waits the given number of seconds before the first retry.</summary>
    /// <remarks>
    /// The delay is the wait before the first retry only. Later waits multiply it by the backoff
    /// factor, so with a factor of 2.0 and 100 ms the waits are 100, 200, 400 ms.
    /// </remarks>
    member this.DelaySeconds(seconds: float) =
        policy <- { policy with Delay = TimeSpan.FromSeconds seconds }
        this

    /// <summary>Tries the operation at most this many times, counting the first try.</summary>
    /// <remarks>
    /// Throws <c>ArgumentOutOfRangeException</c> below 1. The last setting wins: calling this twice
    /// keeps the second value.
    /// </remarks>
    member this.Attempts(count: int) =
        if count < 1 then raise (ArgumentOutOfRangeException(nameof count))
        policy <- { policy with Attempts = count }
        this

    /// <summary>Tries the operation at most this many times, counting the first try.</summary>
    /// <remarks>
    /// Throws <c>ArgumentOutOfRangeException</c> below 1. The last setting wins: calling this twice
    /// keeps the second value.
    /// </remarks>
    member this.Attempts(count: uint32) =
        this.Attempts(int count)

    /// <summary>Multiplies each wait by <c>factor</c>; 1.0 keeps the wait constant.</summary>
    member this.Backoff(factor: float) =
        policy <- { policy with Backoff = factor }
        this

    /// <summary>The policy built so far.</summary>
    member _.Build() = policy
