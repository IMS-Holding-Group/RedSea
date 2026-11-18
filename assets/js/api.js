/* طبقة الاتصال بالخادم: JSON، رمز CSRF، ورسائل أخطاء عامة */
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}
const Api = (() => {
  let csrf = null;
  const setCsrf = (token) => { csrf = token; };
  async function ensureCsrf() {
    if (csrf) { return csrf; }
    const res = await fetch('/api/auth/csrf', { credentials: 'same-origin' });
    const json = await res.json();
    csrf = json.data.csrf;
    return csrf;
  }
  async function request(method, url, data, isForm) {
    const opts = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (method !== 'GET') {
      opts.headers['X-CSRF-Token'] = await ensureCsrf();
      if (isForm) {
        opts.body = data;
      } else if (data !== undefined) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(data);
      }
    }
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      throw new ApiError('تعذر الاتصال بالخادم. تحقق من اتصال الإنترنت.', 0);
    }
    let json = null;
    try {
      json = await res.json();
    } catch (e) {
      throw new ApiError('استجابة غير متوقعة من الخادم.', res.status);
    }
    if (!res.ok || !json.ok) { throw new ApiError(json.error || 'حدث خطأ غير متوقع.', res.status); }
    return json.data;
  }
  return {
    setCsrf,
    get: (url) => request('GET', url),
    post: (url, data) => request('POST', url, data === undefined ? {} : data),
    put: (url, data) => request('PUT', url, data),
    del: (url) => request('DELETE', url, {}),
    upload: (url, formData) => request('POST', url, formData, true)
  };
})();
