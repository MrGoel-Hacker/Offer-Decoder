import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { SmartInput } from "./SmartInput";
import { ReportCheckout } from "./ReportCheckout";
import { PurchasedReportActions } from "./PurchasedReportActions";
import { http } from "@/lib/api";
import { useAuth } from "@/lib/auth";

jest.mock("@/lib/api", () => ({ http: { post: jest.fn(), get: jest.fn() }, errMsg: (_, fallback) => fallback, toPayload: (x) => x }));
jest.mock("@/lib/auth", () => ({ useAuth: jest.fn() }));
jest.mock("./AuthModal", () => ({ AuthModal: () => null }));
jest.mock("react-router-dom", () => ({ Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a> }));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));

let host, root;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  sessionStorage.clear();
  useAuth.mockReturnValue({ user: { name: "Sample" }, authHeaders: () => ({ authorization: "Bearer test-session" }) });
  host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host);
});
afterEach(() => { act(() => root.unmount()); host.remove(); });

test("PDF upload is immediately visible and decode waits for the sign-in gate", async () => {
  const authorize = jest.fn();
  act(() => root.render(<SmartInput country="in" onDecoded={jest.fn()} onQuickScan={jest.fn()} authorize={authorize} />));
  expect(host.querySelector('[data-testid="browse-files-button"]').textContent).toBe(" Choose PDF or photos");
  expect(host.querySelector("textarea")).toBeNull();
  const input = host.querySelector('input[type="file"]');
  Object.defineProperty(input, "files", { value: [new File(["sample"], "offer.pdf", { type: "application/pdf" })] });
  act(() => input.dispatchEvent(new Event("change", { bubbles: true })));
  const decode = host.querySelector('[data-testid="decode-ai-button"]');
  expect(decode.disabled).toBe(false);
  act(() => decode.click());
  expect(authorize).toHaveBeenCalledTimes(1);
  expect(http.post).not.toHaveBeenCalled();
  http.post.mockResolvedValue({ data: { ok: true, fields: { ctc: 1800000 } } });
  await act(async () => authorize.mock.calls[0][0]());
  expect(http.post.mock.calls[0][0]).toBe("/extract/pdf");
  expect(http.post.mock.calls[0][2].headers.authorization).toBe("Bearer test-session");
});

test.each([["in", "₹125", { ctc: 1800000 }], ["us", "$5", { baseSalary: 120000 }]])("%s checkout shows the payment action and sends authenticated offer inputs", async (country, amount, input) => {
  http.post.mockRejectedValue(new Error("offline test"));
  act(() => root.render(<ReportCheckout session={{ country, input }} onReset={jest.fn()} config={{ prices: { IN: { currency: "INR", amount: 12500, original: 50000 }, US: { currency: "USD", amount: 500, original: 2000 } } }} />));
  const button = host.querySelector('[data-testid="pay-unlock-button"]');
  expect(button.textContent).toContain(`Pay ${amount} & unlock report`);
  expect(host.textContent).toContain("Downloadable PDF report to keep");
  await act(async () => button.click());
  expect(http.post).toHaveBeenCalledWith("/payments/checkout", expect.objectContaining({ country, input }), { headers: { authorization: "Bearer test-session" } });
  expect(button.disabled).toBe(false);
  expect(host.querySelector('[role="alert"]')).not.toBeNull();
});

test("a shared-link visitor can download but cannot create new share permissions", () => {
  act(() => root.render(<PurchasedReportActions reportId="sample" allowShare={false} />));
  expect(host.querySelector('[data-testid="download-report-pdf"]')).not.toBeNull();
  expect(host.textContent).not.toContain("Create & copy share link");
  expect(http.post).not.toHaveBeenCalled();
});
