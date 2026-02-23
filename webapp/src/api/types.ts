export interface Photo {
  id: string;
  tg_file_id: string;
  created_at: string;
}

export interface Vote {
  id: string;
  item_id: string;
  user_tg_id: number;
  quantity: number;
}

export interface Item {
  id: string;
  name: string;
  price: number;
  quantity: number;
  votes: Vote[];
}

export interface Member {
  id: string;
  user_tg_id: number;
  display_name: string;
  tip_percent: number | null;
  confirmed: boolean;
  joined_at: string;
}

export interface Session {
  id: string;
  admin_tg_id: number;
  invite_code: string;
  status: string;
  currency: string;
  tip_percent: number;
  created_at: string;
  closed_at: string | null;
  photos: Photo[];
  items: Item[];
  members: Member[];
}

export interface SessionBrief {
  id: string;
  invite_code: string;
  status: string;
  created_at: string;
  member_count: number;
  item_count: number;
}

export interface OcrItem {
  name: string;
  price: number;
  quantity: number;
}

export interface OcrResult {
  items: OcrItem[];
  total: number;
  currency: string;
  total_mismatch: boolean;
}

export interface Share {
  user_tg_id: number;
  display_name: string;
  dishes_total: number;
  tip_amount: number;
  grand_total: number;
}

export interface Quota {
  free_scans_left: number;
  paid_scans: number;
  reset_at: string;
}

export interface VoteResult {
  quantity: number;
  overflow_prevented: boolean;
}
