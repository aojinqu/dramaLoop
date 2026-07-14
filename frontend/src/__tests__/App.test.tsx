import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as api from "../api";
import App from "../App";
import { RunForm } from "../components/RunForm";

vi.mock("../api", () => ({
  createRun: vi.fn(),
  fetchRunDetail: vi.fn(),
  connectRunStream: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

test("renders the episodic single-page shell contract", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: /短剧生成工作台/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/idea/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /开始生成/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /阶段进度/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /实时进度/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /生成结果/i })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /合并成稿/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /artifacts/i, level: 3 })).toBeInTheDocument();

  const timelineSection = screen.getByRole("heading", { name: /阶段进度/i, level: 2 }).closest("section");
  expect(timelineSection).not.toBeNull();
  expect(timelineSection).toHaveTextContent("整季规划");
  expect(timelineSection).toHaveTextContent("最终合并");
});

test("submitting the launch form does not trigger native navigation", () => {
  render(<RunForm onSubmit={() => {}} />);

  const form = screen.getByRole("button", { name: /开始生成/i }).closest("form");
  expect(form).not.toBeNull();

  const submitEvent = fireEvent.submit(form!);

  expect(submitEvent).toBe(false);
});

test("launches an episodic run and renders merged result", async () => {
  const createRun = vi.mocked(api.createRun);
  const fetchRunDetail = vi.mocked(api.fetchRunDetail);
  const connectRunStream = vi.mocked(api.connectRunStream);

  createRun.mockResolvedValue({
    run_id: "20260709-frontend-demo-story",
    status: "running",
    stream_url: "/api/runs/20260709-frontend-demo-story/stream",
  });

  fetchRunDetail.mockResolvedValue({
    run_id: "20260709-frontend-demo-story",
    status: "completed",
    request: {
      idea: "被未婚夫当众退婚后，她转身嫁给了他的死对头",
      style: ["都市情感", "逆袭"],
      audience: "女性向短剧用户",
      constraints: ["节奏快", "结尾有回报"],
      max_iterations: 2,
      length: "short",
      format: "episodic_series",
      episode_count: 12,
      episode_min_words: 500,
      episode_max_words: 800,
      delivery_mode: "stream_and_final",
    },
    stages: [{ name: "episode_generation", status: "completed" }],
    current_stage: null,
    current_episode_number: null,
    completed_episode_count: 12,
    episodes: [
      {
        episode_number: 1,
        title: "婚礼反击",
        status: "completed",
        word_count: 620,
        hook_line: "顾承骁说他知道偷拍视频是谁放的。",
        content: "第1集正文",
      },
    ],
    final_story: "# 第1集 婚礼反击\n\n第1集正文",
    overall_score: null,
    rewrite_focus: null,
    season_summary: "12 集短剧规划完成",
    season_bible: {
      title_candidate: "婚礼反击",
      series_logline: "12 集短剧规划完成",
      core_conflict: "退婚后的反击",
    },
    episode_plan: {
      episodes: [{ episode_number: 1, title: "婚礼反击", core_conflict: "当众退婚" }],
    },
    available_artifacts: ["episodes/episode_01.md", "final_story.md"],
  });

  connectRunStream.mockImplementation((_runId, handlers) => {
    handlers.onMessage({ event: "episode_completed", data: { stage: "episode_generation", iteration: 1 } });
    handlers.onMessage({ event: "run_completed", data: { run_id: "20260709-frontend-demo-story" } });
    return { close() {} } as EventSource;
  });

  render(<App />);

  await userEvent.clear(screen.getByLabelText(/idea/i));
  await userEvent.type(screen.getByLabelText(/idea/i), "被未婚夫当众退婚后，她转身嫁给了他的死对头");
  await userEvent.click(screen.getByRole("button", { name: /开始生成/i }));

  await waitFor(() => {
    expect(screen.getByText(/已完成 12 \/ 12 集/)).toBeInTheDocument();
  });

  await userEvent.click(screen.getByRole("tab", { name: /分集正文/i }));
  expect(screen.getByText(/第1集 · 婚礼反击/)).toBeInTheDocument();
  expect(screen.getByText(/第1集正文/)).toBeInTheDocument();
});

test("does not show placeholder story while a real run is still running", async () => {
  const createRun = vi.mocked(api.createRun);
  const connectRunStream = vi.mocked(api.connectRunStream);

  createRun.mockResolvedValue({
    run_id: "20260709-running-story",
    status: "running",
    stream_url: "/api/runs/20260709-running-story/stream",
  });

  connectRunStream.mockReturnValue({ close() {} } as EventSource);

  render(<App />);

  await userEvent.clear(screen.getByLabelText(/idea/i));
  await userEvent.type(screen.getByLabelText(/idea/i), "女主复仇短剧设定");
  await userEvent.click(screen.getByRole("button", { name: /开始生成/i }));

  await waitFor(() => {
    expect(screen.getByText(/20260709-running-story/)).toBeInTheDocument();
  });

  await userEvent.click(screen.getByRole("tab", { name: /分集正文/i }));
  expect(screen.getByText(/正在等待分集正文/)).toBeInTheDocument();
  expect(screen.queryByText(/婚礼进行到交换戒指的那一刻/)).not.toBeInTheDocument();
});

test("keeps the timeline header out of streaming after a completed run closes the stream", async () => {
  const createRun = vi.mocked(api.createRun);
  const fetchRunDetail = vi.mocked(api.fetchRunDetail);
  const connectRunStream = vi.mocked(api.connectRunStream);

  createRun.mockResolvedValue({
    run_id: "20260709-complete-story",
    status: "running",
    stream_url: "/api/runs/20260709-complete-story/stream",
  });

  fetchRunDetail.mockResolvedValue({
    run_id: "20260709-complete-story",
    status: "completed",
    request: {
      idea: "她在婚礼上反杀前任",
      style: ["都市情感"],
      audience: "女性向短剧用户",
      constraints: ["节奏快"],
      max_iterations: 2,
      length: "short",
      format: "episodic_series",
      episode_count: 12,
      episode_min_words: 500,
      episode_max_words: 800,
      delivery_mode: "stream_and_final",
    },
    stages: [{ name: "episode_generation", status: "completed" }],
    current_stage: null,
    current_episode_number: null,
    completed_episode_count: 12,
    episodes: [],
    final_story: "最终成稿",
    overall_score: null,
    rewrite_focus: null,
    season_summary: "12 集短剧规划完成",
    available_artifacts: ["final_story.md"],
  });

  connectRunStream.mockImplementation((_runId, handlers) => {
    handlers.onMessage({ event: "run_completed", data: { run_id: "20260709-complete-story" } });
    handlers.onError();
    return { close() {} } as EventSource;
  });

  render(<App />);

  await userEvent.clear(screen.getByLabelText(/idea/i));
  await userEvent.type(screen.getByLabelText(/idea/i), "她在婚礼上反杀前任");
  await userEvent.click(screen.getByRole("button", { name: /开始生成/i }));

  const timelineSection = screen.getByRole("heading", { name: /阶段进度/i, level: 2 }).closest("section");
  expect(timelineSection).not.toBeNull();

  await waitFor(() => {
    expect(within(timelineSection!).getByText(/就绪/i)).toBeInTheDocument();
  });

  expect(within(timelineSection!).queryByText(/^生成中$/i)).not.toBeInTheDocument();
});
