import { test, expect } from '@playwright/test';

const BASE_URL = process.env.API_BASE_URL || 'http://localhost:3000';
const PROJECT_IDENTIFIER = 'PR-1';

/**
 * 创建 API 测试接口遵循 FastAPI form 参数规范
 * 必填字段: schema_path (文件路径), script_path (文件路径)
 * 接口路径: POST /api/v2/projects/{project_identifier}/api-tests
 * Content-Type: application/x-www-form-urlencoded
 * 鉴权: 无需鉴权（security: null）
 */
function buildFormData(params: Record<string, string>): string {
  const formData = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    formData.append(key, value);
  });
  return formData.toString();
}

const VALID_FORM_DATA = buildFormData({
  name: '自动创建的 API 测试',
  schema_path: '/tmp/test-schema.json',
  script_path: '/tmp/test-script.py'
});

test.describe('创建 API 测试 - POST /api/v2/projects/{project_identifier}/api-tests', () => {

  // ============ 正常功能测试 ============

  test('TC1-成功创建 API 测试 - 有效参数', async ({ request }) => {
    const response = await request.post(
      `${BASE_URL}/api/v2/projects/${PROJECT_IDENTIFIER}/api-tests`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: VALID_FORM_DATA
      }
    );

    expect(response.status()).toBe(200);
  });

  // ============ 路径参数验证测试 ============

  test('TC2-project_identifier 为空字符串导致路径异常', async ({ request }) => {
    // 空 project_identifier 产生双斜杠 //api-tests，不匹配任何路由
    const response = await request.post(
      `${BASE_URL}/api/v2/projects//api-tests`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: VALID_FORM_DATA
      }
    );

    expect(response.status()).toBe(405);
  });

  test('TC3-project_identifier 为无效值', async ({ request }) => {
    const response = await request.post(
      `${BASE_URL}/api/v2/projects/NON_EXISTENT_PROJECT/api-tests`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: VALID_FORM_DATA
      }
    );

    const status = response.status();
    expect([422, 404]).toContain(status);
  });

  // ============ 请求体验证测试 ============

  test('TC4-缺少请求体', async ({ request }) => {
    const response = await request.post(
      `${BASE_URL}/api/v2/projects/${PROJECT_IDENTIFIER}/api-tests`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      }
    );

    expect(response.status()).toBe(422);
  });

  test('TC5-缺少必填字段 schema_path', async ({ request }) => {
    // 只提供 script_path，缺少 schema_path
    const response = await request.post(
      `${BASE_URL}/api/v2/projects/${PROJECT_IDENTIFIER}/api-tests`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: buildFormData({ script_path: '/tmp/test-script.py' })
      }
    );

    expect(response.status()).toBe(422);
    const data = await response.json();
    expect(data.success).toBe(false);
    expect(data.error).toBe('validation_error');
  });

  test('TC6-无需鉴权 - 不传认证头', async ({ request }) => {
    // 验证接口无需鉴权即可访问
    const response = await request.post(
      `${BASE_URL}/api/v2/projects/${PROJECT_IDENTIFIER}/api-tests`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: VALID_FORM_DATA
      }
    );

    expect(response.status()).toBe(200);
  });
});
