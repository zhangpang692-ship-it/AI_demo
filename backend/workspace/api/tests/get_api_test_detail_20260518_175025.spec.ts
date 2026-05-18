import { test, expect } from '@playwright/test';

// ============================================================
// API 测试：GET /api/v2/projects/{project_identifier}/api-tests/{api_test_id}
// 描述：获取指定 API 测试的详细信息
// 项目 ID: PR-1
// ============================================================

const BASE_URL = process.env.API_BASE_URL || 'https://api.example.com';
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';
const PROJECT_ID = 'PR-1';
const VALID_API_TEST_ID = '6c642565-16fe-4ef9-8bfa-d6ce6f010815';

// 认证请求头
const authHeaders = (token?: string) => ({
  'Authorization': `Bearer ${token || AUTH_TOKEN}`,
  'Content-Type': 'application/json',
});

test.describe('GET /api/v2/projects/{project_identifier}/api-tests/{api_test_id} - 获取 API 测试详情', () => {

  // ============================================================
  // 1. 正常功能测试
  // ============================================================

  test('【正常】成功获取 API 测试详情 - 使用有效的 project_identifier 和 api_test_id', async ({ request }) => {
    // Arrange
    const validToken = AUTH_TOKEN;

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${VALID_API_TEST_ID}`,
      { headers: authHeaders(validToken) }
    );

    // Assert
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toBeDefined();
    // 验证响应包含 API 测试的完整信息
    expect(data).toHaveProperty('success');
  });

  // ============================================================
  // 2. 边界测试
  // ============================================================

  test('【边界】不存在的 api_test_id - 使用 UUID 格式但值不存在', async ({ request }) => {
    // Arrange
    const nonExistentId = '00000000-0000-0000-0000-000000000000';

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${nonExistentId}`,
      { headers: authHeaders() }
    );

    // Assert
    // 不存在的资源应该返回 404 或 422
    expect([404, 422]).toContain(response.status());
  });

  test('【边界】不存在的 project_identifier', async ({ request }) => {
    // Arrange
    const nonExistentProject = 'NONEXIST-PROJECT';

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${nonExistentProject}/api-tests/${VALID_API_TEST_ID}`,
      { headers: authHeaders() }
    );

    // Assert
    expect([404, 422]).toContain(response.status());
  });

  // ============================================================
  // 3. 异常测试
  // ============================================================

  test('【异常】无效的 UUID 格式 - 提供非 UUID 格式的 api_test_id', async ({ request }) => {
    // Arrange
    const invalidId = 'invalid-uuid-format';

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${invalidId}`,
      { headers: authHeaders() }
    );

    // Assert
    // 参数格式验证失败应返回 422
    expect([422, 404]).toContain(response.status());
    if (response.status() === 422) {
      const error = await response.json();
      expect(error).toHaveProperty('detail');
    }
  });

  test('【异常】超长字符串作为 project_identifier', async ({ request }) => {
    // Arrange
    const longProjectId = 'a'.repeat(100);

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${longProjectId}/api-tests/${VALID_API_TEST_ID}`,
      { headers: authHeaders() }
    );

    // Assert
    expect([422, 404]).toContain(response.status());
  });

  // ============================================================
  // 4. 安全测试
  // ============================================================

  test('【安全】缺少认证 Token - 不提供 Authorization 请求头', async ({ request }) => {
    // Arrange - 不设置 Authorization 头

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${VALID_API_TEST_ID}`,
      { headers: { 'Content-Type': 'application/json' } }
    );

    // Assert - 未认证应返回 401
    expect(response.status()).toBe(401);
  });

  test('【安全】无效的 Bearer Token', async ({ request }) => {
    // Arrange
    const invalidToken = 'invalid-token-12345';

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${VALID_API_TEST_ID}`,
      { headers: authHeaders(invalidToken) }
    );

    // Assert - 无效 token 应返回 401 或 403
    expect([401, 403]).toContain(response.status());
  });

  test('【安全】SQL 注入 - 在 api_test_id 中注入 SQL', async ({ request }) => {
    // Arrange
    const sqlInjectionId = "1' OR '1'='1";

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${encodeURIComponent(sqlInjectionId)}`,
      { headers: authHeaders() }
    );

    // Assert - SQL 注入应被拒绝或过滤
    // 不应返回 200 成功响应
    expect(response.status()).not.toBe(200);
    expect([422, 404, 400]).toContain(response.status());
  });

  test('【安全】XSS 攻击 - 在参数中注入脚本标签', async ({ request }) => {
    // Arrange
    const xssPayload = "<script>alert('xss')</script>";

    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${encodeURIComponent(xssPayload)}`,
      { headers: authHeaders() }
    );

    // Assert - XSS 应被过滤
    expect(response.status()).not.toBe(200);
    expect([422, 404, 400]).toContain(response.status());
  });

  // ============================================================
  // 5. 认证 Token 格式测试
  // ============================================================

  test('【安全】空 Token - Authorization 头值为空字符串', async ({ request }) => {
    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${VALID_API_TEST_ID}`,
      { headers: { 'Authorization': '', 'Content-Type': 'application/json' } }
    );

    // Assert
    expect([401, 422]).toContain(response.status());
  });

  test('【安全】Token 无 Bearer 前缀', async ({ request }) => {
    // Act
    const response = await request.get(
      `${BASE_URL}/api/v2/projects/${PROJECT_ID}/api-tests/${VALID_API_TEST_ID}`,
      { headers: { 'Authorization': AUTH_TOKEN, 'Content-Type': 'application/json' } }
    );

    // Assert
    expect([401, 422]).toContain(response.status());
  });
});
