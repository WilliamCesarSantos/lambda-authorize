INSERT INTO users (name, email, password_hash, roles) VALUES
(
    'William Cesar Santos',
    'william_cesar_santos@hotmail.com',
    '$argon2id$v=19$m=65536,t=3,p=4$cfKIYiDHyUhjEEUBT/UAtg$l9DelUkeoA0eRdhkGCO74KcvHtu7NNG5FIx6as6shZM',
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
