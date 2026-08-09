-- Mock 广告账户数据脚本
-- 为用户 zhangtianzhu_1@163.com 添加测试数据

-- 1. 添加 Meta 平台连接
INSERT INTO platform_connections (
    id,
    user_id,
    platform,
    account_id,
    account_name,
    account_secret,
    token_type,
    status,
    created_at,
    updated_at
) VALUES (
    'mock-meta-conn-001',
    '44c57f1e-277d-4f41-b9a7-9691a2227374',
    'Meta',
    'mock_meta_12345',
    'Aniforce 测试账户',
    'mock_secret_key',
    'Bearer',
    'active',
    datetime('now'),
    datetime('now')
);

-- 2. 添加 Meta 子账户绑定（3个广告账户）
INSERT INTO sub_account_bindings (
    id,
    parent_connection_id,
    sub_account_name,
    sub_account_id,
    status,
    created_at,
    updated_at
) VALUES
    ('mock-sub-001', 'mock-meta-conn-001', 'Aniforce Meta 广告账户 01', 'act_1234567890', 'active', datetime('now'), datetime('now')),
    ('mock-sub-002', 'mock-meta-conn-001', 'Aniforce Meta 广告账户 02', 'act_2345678901', 'active', datetime('now'), datetime('now')),
    ('mock-sub-003', 'mock-meta-conn-001', 'Aniforce Meta 广告账户 03', 'act_3456789012', 'active', datetime('now'), datetime('now'));

-- 3. 添加 Google 平台连接
INSERT INTO platform_connections (
    id,
    user_id,
    platform,
    account_id,
    account_name,
    account_secret,
    token_type,
    status,
    created_at,
    updated_at
) VALUES (
    'mock-google-conn-001',
    '44c57f1e-277d-4f41-b9a7-9691a2227374',
    'Google',
    'mock_google_12345',
    'Aniforce Google Ads',
    'mock_secret_key',
    'Bearer',
    'active',
    datetime('now'),
    datetime('now')
);

-- 4. 添加 Google 子账户绑定（2个广告账户）
INSERT INTO sub_account_bindings (
    id,
    parent_connection_id,
    sub_account_name,
    sub_account_id,
    status,
    created_at,
    updated_at,
    bm_customer_id
) VALUES
    ('mock-sub-004', 'mock-google-conn-001', 'Aniforce Google Ads 01', '1234567890', 'active', datetime('now'), datetime('now'), '1234567890'),
    ('mock-sub-005', 'mock-google-conn-001', 'Aniforce Google Ads 02', '2345678901', 'active', datetime('now'), datetime('now'), '2345678901');
