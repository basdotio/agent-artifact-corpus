<?php

// Add this entry to the array returned by config/services.php.

return [
    'innbucks' => [
        'base_url'    => env('INNBUCKS_BASE_URL'),
        'api_key'     => env('INNBUCKS_API_KEY'),
        'username'    => env('INNBUCKS_USERNAME'),
        'password'    => env('INNBUCKS_PASSWORD'),
        'environment' => env('INNBUCKS_ENV', 'test'),
        'token_ttl'   => (int) env('INNBUCKS_TOKEN_TTL', 840),
    ],
];
