declare global {
  namespace App {
    interface Locals { requestId: string }
    interface Error { message: string; request_id?: string }
  }
}

export {};
