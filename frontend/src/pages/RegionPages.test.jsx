import React, { act } from "react";
import { createRoot } from "react-dom/client";
import Home from "./Home";
import SelectRegion from "./SelectRegion";
import { http } from "@/lib/api";

jest.mock("react-router-dom", () => ({ Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a> }));
jest.mock("@/lib/api", () => ({ http: { get: jest.fn() } }));
jest.mock("@/lib/auth", () => ({ useAuth: () => ({ user: { name: "Sample" }, ready: true }) }));
jest.mock("@/components/AuthModal", () => ({ AuthModal: () => null }));
jest.mock("@/components/SmartInput", () => ({ SmartInput: ({ country }) => <div data-testid="input-country">{country}</div> }));
jest.mock("@/components/ManualForm", () => ({ ManualForm: () => null }));
jest.mock("@/components/report/ReportView", () => ({ ReportView: () => null }));

let host, root;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  window.scrollTo = jest.fn(); sessionStorage.clear();
  http.get.mockResolvedValue({ data: { enabled: true } });
  host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host);
});
afterEach(() => { act(() => root.unmount()); host.remove(); });

test("the region selector links to both pages without advertising prices", () => {
  act(() => root.render(<SelectRegion />));
  expect(host.querySelector('[data-testid="select-india"]').getAttribute("href")).toBe("/india");
  expect(host.querySelector('[data-testid="select-usa"]').getAttribute("href")).toBe("/usa");
  expect(host.textContent).not.toMatch(/₹|\$|125|500/);
});

test.each([["in", "₹125", "US$5"], ["us", "US$5", "₹125"]])("%s page uses only its own price and extraction country", async (country, ownPrice, otherPrice) => {
  await act(async () => root.render(<Home country={country} />));
  expect(host.querySelector('[data-testid="input-country"]').textContent).toBe(country);
  expect(host.textContent).toContain(ownPrice);
  expect(host.textContent).not.toContain(otherPrice);
  expect(host.querySelector('[data-testid="country-toggle"]')).toBeNull();
  expect(http.get).toHaveBeenCalledWith(`/payments/config?country=${country}`);
});
