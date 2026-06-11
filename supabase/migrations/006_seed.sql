-- =============================================================================
-- Migration 006: Seed Data
-- Man Matters Products, Formats, Narratives, Hooks
-- =============================================================================

-- =============================================================================
-- PRODUCTS
-- =============================================================================

INSERT INTO products (name, slug, category, description, sort_order) VALUES
-- Hair
('Biotin Gummies',   'biotin-gummies',   'hair',      'Biotin-rich gummies for hair growth and strength',           1),
('Stage 1 Serum',    'stage-1-serum',    'hair',      'Stage 1 hair serum for early hair loss intervention',        2),
('Stage 2',          'stage-2',          'hair',      'Stage 2 hair loss treatment',                                3),
('Stage 3',          'stage-3',          'hair',      'Stage 3 advanced hair loss treatment',                       4),
('Advance Regime',   'advance-regime',   'hair',      'Comprehensive advance hair loss regime',                     5),
-- Wellness
('Magnesium Gummies','magnesium-gummies','wellness',  'Magnesium gummies for stress, sleep and muscle recovery',    6),
('Shilajit Gummies', 'shilajit-gummies', 'wellness',  'Shilajit gummies for energy, stamina and vitality',          7),
-- Fitness
('Creatine Powder',  'creatine-powder',  'fitness',   'Creatine monohydrate powder for strength and performance',   8),
('Creatine Electrolyte', 'creatine-electrolyte', 'fitness', 'Creatine with electrolytes for hydration and performance', 9)
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- FORMATS
-- =============================================================================

INSERT INTO formats (name, slug, format_type, primary_metrics, uses_video_metrics) VALUES
('Reel',                'reel',         'reel',     ARRAY['hook_rate','hold_rate','ctr','link_ctr','cpa','roas'], TRUE),
('Static Image',        'static',       'static',   ARRAY['ctr','link_ctr','cpm','cpc','cpa','roas'],            FALSE),
('Carousel',            'carousel',     'carousel', ARRAY['ctr','link_ctr','cpm','cpc','cpa','roas'],            FALSE),
('Story',               'story',        'story',    ARRAY['ctr','link_ctr','cpc','swipe_rate','cpa'],            FALSE),
('Video (Non-Reel)',     'video',        'static',   ARRAY['hook_rate','hold_rate','ctr','cpa','roas'],           TRUE),
('Collection',          'collection',   'collection', ARRAY['ctr','link_ctr','cpa','roas'],                      FALSE),
('Instant Experience',  'instant-exp',  'instant_experience', ARRAY['ctr','cpa','roas'],                        FALSE)
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- NARRATIVES
-- =============================================================================

INSERT INTO narratives (name, slug, narrative_type, description, example_hook) VALUES
('Myth Busting',          'myth-busting',         'myth_busting',         'Debunking common myths about hair loss, wellness or fitness', 'Everything you know about hair loss is WRONG...'),
('Doctor Recommendation', 'doctor-recommendation','doctor_recommendation','Expert/doctor endorsing the product',                        'Dr. [Name] recommends this for...'),
('Expert Recommendation', 'expert-recommendation','expert_recommendation','Non-doctor expert endorsing the product',                    'As a certified trichologist, I recommend...'),
('Product Demo',          'product-demo',         'product_demo',         'Demonstrating how the product works',                        'Watch how this serum works in just 30 days...'),
('Before After',          'before-after',         'before_after',         'Visual transformation showcase',                             'I went from THIS to THIS in 60 days...'),
('UGC Testimonial',       'ugc-testimonial',      'ugc',                  'Real customer sharing their experience',                     'I was skeptical but after 3 months...'),
('Educational',           'educational',          'educational',          'Educating about the problem and solution',                   'DHT is the real reason you''re losing hair...'),
('Problem Solution',      'problem-solution',     'problem_solution',     'Identifying pain and presenting the product as solution',    'Tired of seeing hair on your pillow every morning?'),
('Social Proof',          'social-proof',         'social_proof',         'Leveraging customer reviews and ratings',                    '50,000 men have tried this and here''s what happened...'),
('Founder Story',         'founder-story',        'founder_story',        'Founder sharing their personal journey',                     'I started this company because I was losing my hair at 25...'),
('Transformation Story',  'transformation-story', 'transformation_story', 'Long-form personal transformation narrative',               'My hair transformation journey over 6 months...'),
('Authority Based',       'authority-based',      'authority_based',      'Leveraging authority figures and credentials',              'Clinically tested. Dermatologist approved...'),
('Comparison',            'comparison',           'comparison',           'Comparing against competitors or alternatives',             'Why this beats everything else you''ve tried...'),
('Lifestyle',             'lifestyle',            'lifestyle',            'Aspirational lifestyle association',                         'Confident. Active. Successful. Start your journey...'),
('Humour',               'humour',               'humour',               'Using comedy to communicate product benefits',              'When your barber starts giving you ''the look''...'),
('Seasonal',             'seasonal',             'seasonal',             'Tying into seasons, occasions or trends',                   'This monsoon, don''t let humidity ruin your hair...'),
('Challenge',            'challenge',            'challenge',            'Issuing a challenge to the viewer',                         'I challenge you to try this for 30 days...'),
('News Jacking',         'news-jacking',         'news_jacking',         'Leveraging current events or trends',                      'Trending: Why Indian men are switching to...')
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- HOOKS
-- =============================================================================

INSERT INTO hooks (name, slug, hook_type, description, example) VALUES
('Doctor Authority',      'doctor-authority',     'authority',      'Opens with a doctor speaking directly',                      'Hi, I am Dr. [Name], and I want to tell you something important about hair loss...'),
('Expert Authority',      'expert-authority',     'authority',      'Opens with an expert credential statement',                  'As a certified trichologist with 15 years of experience...'),
('Pain Agitation',        'pain-agitation',       'problem',        'Opens by amplifying the viewer''s pain point',               'Losing 100+ strands of hair daily? You''re not alone...'),
('Curiosity Gap',         'curiosity-gap',        'curiosity',      'Creates information gap to compel watching',                 'The one ingredient that dermatologists don''t talk about...'),
('Social Proof Number',   'social-proof-number',  'social_proof',   'Opens with impressive customer numbers',                     '50,000 Indian men trust this for their hair...'),
('Shocking Statistic',    'shocking-stat',        'statistic',      'Opens with a surprising fact or number',                     '1 in 3 Indian men will experience hair loss before 30...'),
('Transformation Hook',   'transformation',       'transformation', 'Opens with a dramatic before/after tease',                   'In 90 days, this is what happened to my hair...'),
('Question Hook',         'question-hook',        'question',       'Opens with a relatable question',                            'Still trying to figure out why your hair is thinning?'),
('Myth Statement',        'myth-statement',       'myth_bust',      'Opens by stating a myth about to be busted',                 'Everyone told me oiling my hair would stop hair fall. They were wrong.'),
('Urgency Hook',          'urgency-hook',         'urgency',        'Creates time-based urgency',                                 'If you''re above 25 and still ignoring this, listen up...'),
('Relatability Hook',     'relatability-hook',    'relatability',   'Opens with a highly relatable scenario',                     'Every morning in the shower... watching hair go down the drain...'),
('Challenge Hook',        'challenge-hook',       'challenge',      'Issues a direct challenge to the viewer',                   'I bet you''ve never tried a hair product like this...'),
('Announcement Hook',     'announcement-hook',    'announcement',   'Opens with exciting news or launch',                         'We just launched something that changed how we grow hair...'),
('Comparison Hook',       'comparison-hook',      'comparison',     'Opens by comparing to alternatives',                        'Minoxidil. Finasteride. Or this natural alternative...')
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- ARCHETYPES
-- =============================================================================

INSERT INTO archetypes (name, slug, description, typical_hook_type, typical_narrative, typical_format, typical_creator) VALUES
('Doctor UGC',              'doctor-ugc',           'Doctor speaking directly to camera about the product',              'authority',      'doctor_recommendation', 'reel',     'doctor'),
('Customer Testimonial UGC','customer-ugc',         'Real customer sharing authentic experience on camera',              'relatability',   'ugc',                   'reel',     'customer'),
('Founder Talking Head',    'founder-talking-head', 'Founder/team member speaking about the brand',                     'authority',      'founder_story',         'reel',     'founder'),
('Product Demo Static',     'product-demo-static',  'Clean product photography with benefit copy',                      'problem',        'product_demo',          'static',   'none'),
('Before After Reel',       'before-after-reel',    'Side-by-side or sequential transformation video',                  'transformation', 'before_after',          'reel',     'customer'),
('Educational Explainer',   'educational-explainer','Informational content explaining the science or mechanism',        'curiosity',      'educational',           'reel',     'expert'),
('Problem Agitation',       'problem-agitation',    'Emotionally charged content focused on the pain point',           'problem',        'problem_solution',      'reel',     'customer'),
('Authority Static',        'authority-static',     'Credential-forward static ad with doctor or expert',              'authority',      'authority_based',       'static',   'doctor'),
('Social Proof Carousel',   'social-proof-carousel','Carousel of customer reviews and results',                        'social_proof',   'social_proof',          'carousel', 'customer'),
('Comparison Ad',           'comparison-ad',        'Direct comparison against alternatives/competitors',               'comparison',     'comparison',            'static',   'none'),
('Transformation Story',    'transformation-story-arch', 'Long-form personal journey with emotional arc',             'transformation', 'transformation_story',  'reel',     'customer'),
('Meme Style',              'meme-style',           'Humour-driven content using meme formats',                        'relatability',   'humour',                'reel',     'none'),
('Influencer Review',       'influencer-review',    'Influencer or creator sharing their experience',                  'social_proof',   'ugc',                   'reel',     'influencer'),
('Myth Busting Explainer',  'myth-busting-exp',     'Authoritative content debunking common myths',                    'myth_bust',      'myth_busting',          'reel',     'doctor'),
('Lifestyle Aspiration',    'lifestyle-aspiration', 'Aspirational content showing confident, successful men',          'relatability',   'lifestyle',             'reel',     'actor')
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- DEFAULT ADMIN USER
-- =============================================================================

-- Password will be set by migrate.ps1 after container starts
-- Placeholder hash (will be overwritten by migration script)
INSERT INTO users (email, hashed_password, full_name, role) VALUES
('admin@manmatters.com',
 '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
 'Man Matters Admin',
 'admin')
ON CONFLICT (email) DO NOTHING;

-- =============================================================================
-- META AD ACCOUNTS (ManMatters2025 business — confirmed 2026-06-04)
-- business_id: 3767985453466438
-- =============================================================================

INSERT INTO meta_accounts (account_id, account_name, currency, timezone, business_id, is_active) VALUES
('act_920799776816968',   'MM25',        'INR', 'Asia/Kolkata', '3767985453466438', TRUE),
('act_2080540322400218',  'Nutrition25', 'INR', 'Asia/Kolkata', '3767985453466438', TRUE)
ON CONFLICT (account_id) DO NOTHING;
