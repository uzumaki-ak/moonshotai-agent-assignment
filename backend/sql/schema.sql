-- this file creates core tables for local postgres setup
create table if not exists brands (
    id serial primary key,
    name varchar(120) not null unique,
    slug varchar(140) not null unique,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists products (
    id serial primary key,
    brand_id int not null references brands(id) on delete cascade,
    asin varchar(20) not null unique,
    title text not null,
    url text not null,
    category varchar(255),
    size varchar(255),
    price numeric(10,2),
    list_price numeric(10,2),
    discount_percent float,
    rating float,
    review_count int,
    last_scraped_at timestamptz,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_products_brand on products(brand_id);

create table if not exists reviews (
    id serial primary key,
    product_id int not null references products(id) on delete cascade,
    review_id varchar(64),
    title varchar(512),
    content text not null,
    rating float,
    sentiment_score float,
    sentiment_label varchar(20),
    review_date date,
    verified_purchase boolean,
    helpful_votes int,
    raw_payload jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_reviews_product on reviews(product_id);
create index if not exists idx_reviews_sentiment on reviews(sentiment_label);

create table if not exists themes (
    id serial primary key,
    brand_id int references brands(id) on delete cascade,
    product_id int references products(id) on delete cascade,
    theme_type varchar(40) not null,
    aspect varchar(80) not null,
    mention_count int not null default 0,
    avg_sentiment float,
    sample_quotes jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_themes_brand on themes(brand_id);
create index if not exists idx_themes_product on themes(product_id);

create table if not exists brand_metrics (
    id serial primary key,
    brand_id int not null references brands(id) on delete cascade,
    snapshot_date date not null,
    avg_price float,
    avg_discount_pct float,
    avg_rating float,
    total_reviews int,
    sentiment_score float,
    premium_index float,
    value_for_money float,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create unique index if not exists uq_brand_metrics_brand_date on brand_metrics(brand_id, snapshot_date);

create table if not exists pipeline_jobs (
    id varchar(36) primary key,
    job_type varchar(40) not null,
    status varchar(20) not null,
    params jsonb,
    result jsonb,
    error_message text,
    started_at timestamptz default now(),
    completed_at timestamptz
);

create table if not exists insights (
    id serial primary key,
    insight_type varchar(40) not null,
    title varchar(200) not null,
    body text not null,
    confidence float,
    payload jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
