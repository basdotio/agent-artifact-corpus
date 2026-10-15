<?php

namespace App\Exceptions;

use RuntimeException;

class InnBucksException extends RuntimeException
{
    public function __construct(
        string $message,
        public readonly array $response = [],
        public readonly ?string $traceId = null,
        public readonly ?int $httpStatus = null,
    ) {
        parent::__construct($message);
    }
}
