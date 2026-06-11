export const PRODUCTS = [
  { slug: "biotin-gummies", name: "Biotin Gummies", category: "hair" as const },
  { slug: "stage-1-serum", name: "Stage 1 Serum", category: "hair" as const },
  { slug: "stage-2", name: "Stage 2", category: "hair" as const },
  { slug: "stage-3", name: "Stage 3", category: "hair" as const },
  { slug: "advance-regime", name: "Advance Regime", category: "hair" as const },
  { slug: "magnesium-gummies", name: "Magnesium Gummies", category: "wellness" as const },
  { slug: "shilajit-gummies", name: "Shilajit Gummies", category: "wellness" as const },
  { slug: "creatine-powder", name: "Creatine Powder", category: "fitness" as const },
  { slug: "creatine-electrolyte", name: "Creatine Electrolyte", category: "fitness" as const },
];

export const NARRATIVES = [
  "myth_busting", "expert_recommendation", "doctor_recommendation",
  "product_demo", "before_after", "ugc", "testimonial", "educational",
  "comparison", "problem_solution", "founder_story", "transformation_story",
  "authority_based", "social_proof", "lifestyle", "humour", "challenge",
  "news_jacking", "seasonal",
];

export const HOOK_TYPES = [
  "authority", "problem", "curiosity", "social_proof", "question",
  "statistic", "shock", "transformation", "urgency", "relatability",
  "myth_bust", "challenge", "announcement", "comparison",
];

export const CREATOR_TYPES = [
  "doctor", "customer", "founder", "actor", "influencer", "expert", "celebrity", "animated", "none",
];

export const FORMATS = [
  "reel", "static", "carousel", "story", "video", "collection", "instant_experience",
];

export const FATIGUE_STAGES = ["healthy", "watch", "fatiguing", "fatigued", "insufficient_data"];

export const COMPETITORS = [
  "Beardo", "Ustraa", "The Man Company", "Bombay Shaving Company",
  "Mars by GHC", "Nourish Mantra", "Sheopal's", "Wow Skin Science", "mCaffeine",
];

export const NAV_ITEMS = [
  { href: "/", label: "Executive", icon: "LayoutDashboard" },
  { href: "/library", label: "Creative Library", icon: "Grid2X2" },
  { href: "/fatigue", label: "Fatigue Monitor", icon: "Activity" },
  { href: "/predictor", label: "Creative Predictor", icon: "Sparkles" },
  { href: "/genome", label: "Creative Genome", icon: "Dna" },
  { href: "/competitors", label: "Competitors", icon: "Eye" },
  { href: "/insights", label: "AI Insights", icon: "Lightbulb" },
];
