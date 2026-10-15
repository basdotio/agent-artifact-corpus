<?php

namespace App\Jobs;

use App\Models\Order;
use App\Services\InnBucks;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Throwable;

class PollInnBucksCode implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 1;

    public function __construct(public Order $order, public int $attempt = 1) {}

    public function handle(InnBucks $innbucks): void
    {
        try {
            $res = $innbucks->inquireCode($this->order->innbucks_code);
        } catch (Throwable $e) {
            report($e);
            $res = [];                             // try again at the next check
        }

        if (InnBucks::isPaid($res)) {
            $this->order->markPaid(authNumber: $res['authNumber'] ?? null);
            return;
        }
        if (InnBucks::isFinal($res)) {             // Expired or Timed Out
            $this->order->markInnBucksCodeExpired();
            return;
        }
        if ($this->attempt >= 22) {                // ~11 minutes: the code has expired by now
            $this->order->markPaymentUnknown();    // review it; never call it failed
            return;
        }

        self::dispatch($this->order, $this->attempt + 1)->delay(now()->addSeconds(30));
    }
}
