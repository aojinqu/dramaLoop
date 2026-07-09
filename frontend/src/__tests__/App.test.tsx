import { render, screen } from "@testing-library/react";
import App from "../App";

test("renders the Task 4 single-page shell contract", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: /dramaloop web demo/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/idea/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /launch run/i })).toBeInTheDocument();
  expect(screen.getByText(/stage timeline/i)).toBeInTheDocument();
  expect(screen.getByText(/event stream/i)).toBeInTheDocument();
  expect(screen.getByText(/final story/i)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /summary/i, level: 3 })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /artifacts/i, level: 3 })).toBeInTheDocument();

  const timelineSection = screen.getByRole("heading", { name: /stage timeline/i, level: 2 }).closest("section");
  expect(timelineSection).not.toBeNull();
  expect(timelineSection).toHaveTextContent("premise_refinement");
  expect(timelineSection).toHaveTextContent("final_assembly");
});

test("submitting the launch form does not navigate away from the SPA shell", () => {
  render(<App />);

  const form = screen.getByRole("button", { name: /launch run/i }).closest("form");
  expect(form).not.toBeNull();

  const submitEvent = new Event("submit", { bubbles: true, cancelable: true });
  form!.dispatchEvent(submitEvent);

  expect(submitEvent.defaultPrevented).toBe(true);
});
