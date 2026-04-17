export type Tab = "library" | "chat";
export type Theme = "light" | "dark";
export type Provider = "ollama" | "openai";

export type Job = {
  id: string;
  url: string;
  language: string | null;
  whisper_model: string;
  force: boolean;
  status: "queued" | "running" | "completed" | "partial" | "failed";
  stage: string;
  progress: number;
  current_video: string | null;
  errors: string[];
  source_ids: string[];
  video_ids: string[];
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type SourceSummary = {
  id: string;
  type: string;
  url: string;
  title: string;
  playlist_id: string | null;
  channel: string | null;
  video_count: number;
  job_id: string;
  created_at: string;
  updated_at: string;
};

export type VideoSummary = {
  id: string;
  source_id: string;
  youtube_id: string;
  playlist_id: string | null;
  url: string;
  title: string;
  channel: string | null;
  duration_sec: number | null;
  audio_path: string | null;
  transcript_json_path: string | null;
  transcript_txt_path: string | null;
  transcript_srt_path: string | null;
  language: string | null;
  status: string;
  error: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type SourceDetail = SourceSummary & {
  videos: VideoSummary[];
};

export type Transcript = {
  video_id: string;
  text: string;
  language: string | null;
  segments: { id: number; start: number; end: number; text: string }[];
};

export type SearchResponse = {
  query: string;
  results: unknown[];
  context: string;
};

export type ChatModel = {
  provider: Provider;
  id: string;
  label: string;
  available: boolean;
};

export type ChatModels = {
  local: ChatModel[];
  online: ChatModel[];
};

export type ConversationSummary = {
  id: string;
  title: string;
  model_provider: Provider;
  model_id: string;
  created_at: string;
  updated_at: string;
  last_message: string | null;
  message_count: number;
};

export type Citation = {
  index: number;
  title: string;
  text: string;
  score: number;
  url: string | null;
  source_id: string | null;
  video_id: string | null;
  playlist_id: string | null;
  context_item_id: string | null;
  context_type: string | null;
  start_sec: number | null;
  end_sec: number | null;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  text: string;
  citations: Citation[];
  model_provider: Provider | null;
  model_id: string | null;
  created_at: string;
};

export type ContextItem = {
  id: string;
  conversation_id: string;
  type: "manual" | "web" | "source" | "video" | "playlist";
  title: string;
  url: string | null;
  text: string | null;
  source_id: string | null;
  video_id: string | null;
  playlist_id: string | null;
  status: string;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: ChatMessage[];
  context_items: ContextItem[];
};
