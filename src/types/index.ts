export type ClothingCategory =
  | 'tops'
  | 'bottoms'
  | 'outerwear'
  | 'shoes'
  | 'accessories';

export type UserRole = 'user' | 'admin';

export interface UserAccount {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  password?: string;
  avatarUrl?: string;
  vipStatus?: string;
  createdAt: string;
}

export interface WardrobeItem {
  id: string;
  title: string;
  category: ClothingCategory;
  color: string;
  season: 'all' | 'spring/summer' | 'autumn/winter';
  style: string[]; // e.g. ['casual', 'business', 'minimalism']
  tags: string[];
  imageUrl: string;
  brand?: string | null;
  material?: string | null;
  embeddingSnippet?: string | null;
  uploadedAt: string;
  imagePath?: string | null;
  weather?: WeatherAttributes | null;
}

// Optional curated facts used by the RAG module. Missing values mean unknown.
export interface WeatherAttributes {
  temperature_min?: number | null;
  temperature_max?: number | null;
  waterproof?: boolean | null;
  windproof?: boolean | null;
  open_shoes?: boolean | null;
}

export type RetrievalMode = 'bm25' | 'dense' | 'hybrid' | 'visual' | 'multimodal';

export interface RetrievalCandidate {
  item: WardrobeItem;
  score: number;
  bm25_score?: number | null;
  bm25_rank?: number | null;
  dense_distance?: number | null;
  dense_rank?: number | null;
  visual_distance?: number | null;
  visual_rank?: number | null;
  bm25_contribution: number;
  dense_contribution: number;
  visual_contribution: number;
  anchored: boolean;
  fallback: boolean;
}

// Mirrors Python RetrievalResult; it is retrieval diagnostics, not an LLM answer.
export interface RetrievalResult {
  user_id: string;
  query: string;
  mode: RetrievalMode;
  alpha: number;
  visual_weight: number;
  rrf_c: number;
  candidates_by_slot: Record<ClothingCategory, RetrievalCandidate[]>;
  required_slots: ClothingCategory[];
  missing_slots: ClothingCategory[];
  context: {
    occasion?: string | null;
    weather?: string | null;
    vibe?: string | null;
    temperature_c?: number | null;
    rain?: boolean | null;
    wind?: boolean | null;
  };
  anchor_item_id?: string | null;
  warnings: string[];
  timings_ms: Record<string, number>;
  wardrobe_revision: string;
  model_fingerprint: string;
  score_method: string;
}

export interface OutfitLook {
  id: string;
  title: string;
  description: string;
  occasion: string;
  items: WardrobeItem[];
  stylistReasoning: string;
  matchScore: number;
  confidenceTips: string[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  suggestedOutfit?: OutfitLook;
  referencedItemIds?: string[];
  isThinking?: boolean;
}

export interface StylistHistoryMessage {
  sender: ChatMessage['sender'];
  text: string;
  hasOutfit?: boolean;
}

export interface ChatThread {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface UserPreferences {
  occasion: string;
  weather: string;
  vibe: string;
}
