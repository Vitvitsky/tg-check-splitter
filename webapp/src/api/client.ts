let _getInitData: (() => string) | null = null;

export function setInitDataProvider(fn: () => string) {
  _getInitData = fn;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: unknown,
  ) {
    super(`API error ${status}`);
  }
}

export async function fetchApi<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const initData = _getInitData?.() ?? "";
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `tma ${initData}`,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data);
  }
  return res.json();
}

export async function fetchApiNoBody(
  url: string,
  options?: RequestInit,
): Promise<void> {
  const initData = _getInitData?.() ?? "";
  const res = await fetch(url, {
    ...options,
    headers: {
      Authorization: `tma ${initData}`,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data);
  }
}
