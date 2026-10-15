export type TryOnImage = {
  product: string;
  model: string;
  url: string;
  logo?: string;
};

export type TryOnJob = {
  id: string;
  status: "pending" | "running" | "succeeded" | "failed";
  try_on_images: TryOnImage[];
  error: string | null;
};

export async function createTryOnJob(input: {
  products: File[];
  models: File[];
  logos: File[];
  assignments?: Record<string, string> | Record<string, Record<string, string>>;
}): Promise<TryOnJob> {
  const form = new FormData();
  for (const file of input.products) {
    form.append("products", file);
  }
  for (const file of input.models) {
    form.append("models", file);
  }
  for (const file of input.logos) {
    form.append("logos", file);
  }
  if (input.assignments && Object.keys(input.assignments).length > 0) {
    form.append("apparelColorAssignments", JSON.stringify(input.assignments));
  }
  const response = await fetch("/try-on-jobs", { method: "POST", body: form });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<TryOnJob>;
}

export async function getTryOnJob(id: string): Promise<TryOnJob> {
  const response = await fetch(`/try-on-jobs/${id}`);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<TryOnJob>;
}

export async function waitForJob(
  id: string,
  onStatus: (job: TryOnJob) => void,
): Promise<TryOnJob> {
  for (;;) {
    const job = await getTryOnJob(id);
    onStatus(job);
    if (job.status === "succeeded" || job.status === "failed") {
      return job;
    }
    await new Promise((resolve) => {
      setTimeout(resolve, 1200);
    });
  }
}

async function readError(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // fall through
  }
  return text || `请求失败 ${response.status}`;
}
