INSERT INTO users (name, email, password_hash, roles) VALUES
(
    'William Cesar Santos',
    'william_cesar_santos@hotmail.com',
    '$argon2id$v=19$m=65536,t=3,p=4$oMI7dPuZD9JmemIhXLr1Qw$qfsUbmhrCysvix+/ycXcCqjjWVdpaD/R2Qayxil3CN4',
    '{admin}'
),
(
    'Ana Paula',
    'ana@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$1XiN0Gm0+b3MIVTHpCzOXg$qY+CJc3mhKHrsE+8yW+4ivEGZvjJyZ3/Ljj9Feb5YPw',
    '{}'
),
(
    'Carlos Eduardo',
    'carlos@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$jmlcdLHM9RST0ADLs+yMkA$F+i3PhNNvgxhp0CKGaIoCXDkQu2dyAy2fUP78gUwwaE',
    '{}'
);
