export type ClothingCategory =
  | 'tops'
  | 'bottoms'
  | 'outerwear'
  | 'shoes'
  | 'accessories';

export interface WardrobeItem {
  id: string;
  title: string;
  category: ClothingCategory;
  color: string;
  season: 'all' | 'spring/summer' | 'autumn/winter';
  style: string[]; // e.g. ['casual', 'business', 'minimalism']
  tags: string[];
  imageUrl: string;
  brand?: string;
  material?: string;
  embeddingSnippet?: string;
  uploadedAt: string;
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
