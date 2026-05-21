export interface Plan {
  plan_name: string;
  display_name: string;
  price: number;
  websites_limit: number | null;
  menu_items_limit: number | null;
  ai_hero_limit: number | null;
  ai_images_limit: number | null;
  delivery_zones_limit: number | null;
  riders_limit: number | null;
  feature_list: string[];
}

export interface SubscriptionStatus {
  plan_name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  days_remaining: number;
  auto_renew: boolean;
  is_expired: boolean;
}

export interface Addon {
  type: string;
  name: string;
  description: string;
  price: number;
}

export interface UsageData {
  used: number;
  limit: number | null;
  percentage: number;
  unlimited: boolean;
  addon_credits: number;
}

export interface UsageResponse {
  plan: {
    name: string;
    status: string;
    days_remaining: number;
    end_date: string | null;
    is_expired: boolean;
  };
  usage: {
    websites?: UsageData;
    menu_items?: UsageData;
    ai_hero?: UsageData;
    ai_images?: UsageData;
    delivery_zones?: UsageData;
    riders?: UsageData;
  };
  addon_prices?: Record<string, number>;
}
