import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

# Page config
st.set_page_config(
    page_title="Clash of Clans Analytics",
    page_icon="⚔️",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_engine():
    return create_engine(st.secrets["db_url"])

try:
    engine = get_engine()
except Exception as e:
    st.error(f"Could not connect to the database: {e}")
    st.stop()

def query(sql):
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            return df
    except Exception as e:
        st.error(f"Database query failed: {e}")
        st.stop()

# Title
st.title("⚔️ Clash of Clans — Player Analytics Dashboard")
st.markdown("*Data Analyst Intern Project · OVGU Magdeburg · Digital Engineering M.Sc.*")
st.divider()

# ── KPI METRICS ROW ──────────────────────────────────────────
@st.cache_data
def load_kpi_data():
    df = query("SELECT COUNT(*) AS c FROM players")
    if df is None or df.empty:
        return None
    return {
        'total_players': query("SELECT COUNT(*) AS c FROM players").iloc[0]['c'],
        'total_clans':   query("SELECT COUNT(*) AS c FROM clans").iloc[0]['c'],
        'total_wars':    query("SELECT COUNT(*) AS c FROM wars").iloc[0]['c'],
        'high_churn':    query("SELECT COUNT(*) AS c FROM players WHERE churn_risk_score >= 0.6").iloc[0]['c'],
        'avg_trophies':  query("SELECT ROUND(AVG(trophies)) AS c FROM players").iloc[0]['c'],
    }

kpis = load_kpi_data()
if kpis is None:
    st.error("Could not load dashboard data. Please try again later.")
    st.stop()

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Players",  f"{kpis['total_players']:,}")
kpi2.metric("Total Clans",    f"{kpis['total_clans']:,}")
kpi3.metric("Total Wars",     f"{kpis['total_wars']:,}")
kpi4.metric("High Churn Risk",f"{kpis['high_churn']:,}")
kpi5.metric("Avg Trophies",   f"{int(kpis['avg_trophies']):,}")

st.divider()

# ── SIDEBAR NAVIGATION ───────────────────────────────────────
page = st.sidebar.radio("Select Analysis", [
    "📈 Progression Analysis",
    "⚔️ War Performance",
    "⏱️ Attack Duration",
    "🏆 Clan Analysis",
    "💀 Churn Risk",
    "🎯 Donation Behavior"
])

# ── PAGE 1 — PROGRESSION ANALYSIS ───────────────────────────
if page == "📈 Progression Analysis":
    st.header("📈 Progression Analysis")
    st.markdown("*Where do players get stuck in their upgrade journey?*")

    @st.cache_data
    def load_progression_data():
        return query("""
        SELECT
            p.town_hall_level,
            ROUND(AVG(CASE WHEN t.troop_type = 'elixir_troop'
                THEN t.level / t.max_level * 100 END), 2) AS elixir_troop,
            ROUND(AVG(CASE WHEN t.troop_type = 'dark_elixir_troop'
                THEN t.level / t.max_level * 100 END), 2) AS dark_elixir_troop,
            ROUND(AVG(CASE WHEN t.troop_type = 'siege_machine'
                THEN t.level / t.max_level * 100 END), 2) AS siege_machine,
            ROUND(AVG(CASE WHEN t.troop_type = 'pet'
                THEN t.level / t.max_level * 100 END), 2) AS pet,
            ROUND(AVG(CASE WHEN t.troop_type = 'elixir_spell'
                THEN t.level / t.max_level * 100 END), 2) AS elixir_spell,
            ROUND(AVG(CASE WHEN t.troop_type = 'dark_spell'
                THEN t.level / t.max_level * 100 END), 2) AS dark_spell
        FROM players p
        JOIN troop_levels t ON p.player_tag = t.player_tag
        WHERE t.village = 'home'
        AND p.town_hall_level BETWEEN 8 AND 18
        GROUP BY p.town_hall_level
        ORDER BY p.town_hall_level
    """)

    df_prog = load_progression_data()

    fig1 = px.line(
        df_prog,
        x='town_hall_level',
        y=['elixir_troop', 'dark_elixir_troop', 'siege_machine', 'pet', 'elixir_spell', 'dark_spell'],
        title='Average upgrade completion % by category and Town Hall level',
        labels={'town_hall_level': 'Town Hall Level', 'value': 'Avg Completion %', 'variable': 'Category'},
        markers=True,
        color_discrete_map={
            'elixir_troop':      '#E91E8C',
            'dark_elixir_troop': '#1A0A2E',
            'siege_machine':     '#F06292',
            'pet':               '#4A1A6B',
            'elixir_spell':      '#CE93D8',
            'dark_spell':        '#0D001A',
        },
    )
    fig1.update_traces(line=dict(dash='dash', width=2.5), selector=dict(name='elixir_spell'))
    fig1.update_traces(line=dict(dash='dot',  width=2.5), selector=dict(name='dark_spell'))
    fig1.update_layout(hovermode='x unified')
    st.plotly_chart(fig1, use_container_width=True)

    st.info("💡 **Key Insight:** Pets and siege machines consistently lag behind other categories — dark elixir scarcity is the primary bottleneck for high-TH players.")

    # Q1b — bottom 2 per category
    st.subheader("Most underupgraded troops at TH15-18")

    @st.cache_data
    def load_bottleneck_data():
        return query("""
            WITH ranked AS (
                SELECT
                    t.troop_name, t.troop_type, p.town_hall_level,
                    ROUND(AVG(t.level / t.max_level * 100), 2) AS avg_completion_pct,
                    COUNT(DISTINCT p.player_tag) AS total_players,
                    ROW_NUMBER() OVER (
                        PARTITION BY t.troop_type, p.town_hall_level
                        ORDER BY AVG(t.level / t.max_level * 100) ASC
                    ) AS rnk
                FROM troop_levels t
                JOIN players p ON t.player_tag = p.player_tag
                WHERE t.village = 'home'
                AND t.troop_type IN ('elixir_troop', 'dark_elixir_troop', 'siege_machine', 'pet')
                AND p.town_hall_level BETWEEN 15 AND 18
                GROUP BY t.troop_name, t.troop_type, p.town_hall_level
                HAVING COUNT(DISTINCT p.player_tag) > 100
            )
            SELECT town_hall_level, troop_type, troop_name, avg_completion_pct, total_players
            FROM ranked WHERE rnk <= 2
            ORDER BY town_hall_level, avg_completion_pct ASC
        """)

    df_bottleneck = load_bottleneck_data()
    if df_bottleneck is None or df_bottleneck.empty:
        st.warning("No bottleneck data available.")
        st.stop()
    th_levels = sorted(df_bottleneck['town_hall_level'].unique())

    fig2 = make_subplots(
        rows=len(th_levels), cols=1,
        subplot_titles=[f'TH {th}' for th in th_levels],
        vertical_spacing=0.10
    )

    color_map = {
        'elixir_troop':       '#E91E8C',
        'dark_elixir_troop':  '#1A0A2E',
        'siege_machine':      '#F06292',
        'pet':                '#4A1A6B',
    }
    shown_legend = set()

    for i, th in enumerate(th_levels, 1):
        df_th = (df_bottleneck[df_bottleneck['town_hall_level'] == th]
                 .sort_values('avg_completion_pct', ascending=True))
        for _, row in df_th.iterrows():
            ttype = row['troop_type']
            show_leg = ttype not in shown_legend
            if show_leg:
                shown_legend.add(ttype)
            fig2.add_trace(
                go.Bar(
                    x=[row['avg_completion_pct']],
                    y=[row['troop_name']],
                    orientation='h',
                    marker_color=color_map.get(ttype, 'gray'),
                    name=ttype.replace('_', ' ').title(),
                    text=[f"  {row['avg_completion_pct']}%"],
                    textposition='outside',
                    cliponaxis=False,
                    showlegend=show_leg,
                    legendgroup=ttype,
                ),
                row=i, col=1
            )
        fig2.update_yaxes(
            categoryorder='array',
            categoryarray=df_th.sort_values('avg_completion_pct', ascending=False)['troop_name'].tolist(),
            tickfont=dict(size=12),
            row=i, col=1
        )
        fig2.update_xaxes(
            range=[0, 125],
            showticklabels=(i == len(th_levels)),
            title_text='Avg Completion %' if i == len(th_levels) else '',
            row=i, col=1
        )

    fig2.update_layout(
        title='Bottom 2 most underupgraded troops per category (TH15-18)',
        height=1400,
        margin=dict(l=20, r=60, t=60, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── PAGE 2 — WAR PERFORMANCE ─────────────────────────────────
elif page == "⚔️ War Performance":
    st.header("⚔️ War Performance")
    st.markdown("*Hero completion vs attack success and attack duration analysis*")

    @st.cache_data
    def load_hero_data():
        return query("""
            SELECT
                CASE
                    WHEN avg_hero.hero_pct < 25 THEN '0-25%'
                    WHEN avg_hero.hero_pct < 50 THEN '25-50%'
                    WHEN avg_hero.hero_pct < 75 THEN '50-75%'
                    ELSE '75-100%'
                END AS hero_bucket,
                ROUND(AVG(wa.stars), 2) AS avg_stars,
                ROUND(AVG(wa.destruction_pct), 2) AS avg_destruction,
                COUNT(wa.id) AS total_attacks
            FROM war_attacks wa
            JOIN (
                SELECT player_tag, AVG(level / max_level * 100) AS hero_pct
                FROM hero_levels
                WHERE village = 'home'
                AND hero_name IN ('Barbarian King', 'Archer Queen',
                                  'Grand Warden', 'Royal Champion', 'Minion Prince')
                GROUP BY player_tag
            ) avg_hero ON wa.attacker_tag = avg_hero.player_tag
            GROUP BY hero_bucket
            ORDER BY avg_stars DESC
        """)

    @st.cache_data
    def load_war_duration_data():
        return query("""
            SELECT
                CASE
                    WHEN duration_seconds < 60 THEN 'Under 60s'
                    WHEN duration_seconds < 100 THEN '60-100s'
                    WHEN duration_seconds < 140 THEN '100-140s'
                    ELSE 'Over 140s'
                END AS duration_bucket,
                ROUND(AVG(stars), 2) AS avg_stars,
                ROUND(AVG(destruction_pct), 2) AS avg_destruction,
                COUNT(*) AS total_attacks,
                ROUND(SUM(CASE WHEN stars = 3 THEN 1 ELSE 0 END) * 100.0
                    / COUNT(*), 2) AS three_star_rate
            FROM war_attacks
            WHERE duration_seconds > 0
            GROUP BY duration_bucket
            ORDER BY avg_stars DESC
        """)

    col1, col2 = st.columns(2)

    with col1:
        df_hero = load_hero_data()
        fig3 = px.bar(
            df_hero,
            x='hero_bucket',
            y='avg_stars',
            color='avg_destruction',
            title='Hero completion vs average war stars',
            labels={'hero_bucket': 'Hero Completion', 'avg_stars': 'Avg Stars'},
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        df_duration = load_war_duration_data()
        fig4 = px.bar(
            df_duration,
            x='duration_bucket',
            y='three_star_rate',
            color='avg_stars',
            title='Attack duration vs 3-star rate',
            labels={'duration_bucket': 'Attack Duration', 'three_star_rate': '3-Star Rate %'},
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.info("💡 **Key Insight:** The optimal attack window is 100-140 seconds with 78% 3-star rate. Fully upgraded heroes outperform underupgraded ones by 7% destruction.")

# ── PAGE 3 — ATTACK DURATION ─────────────────────────────────
elif page == "⏱️ Attack Duration":
    st.header("⏱️ Attack Duration Analysis")
    st.markdown("*Is there a relationship between attack duration and stars earned?*")

    @st.cache_data
    def load_stars_data():
        return query("""
            SELECT
                stars,
                COUNT(*) AS total_attacks,
                ROUND(AVG(duration_seconds), 2) AS avg_duration,
                ROUND(AVG(destruction_pct), 2) AS avg_destruction
            FROM war_attacks
            WHERE duration_seconds > 0
            AND stars IS NOT NULL
            GROUP BY stars
            ORDER BY stars
        """)

    @st.cache_data
    def load_duration_buckets():
        return query("""
            SELECT
                CASE
                    WHEN duration_seconds < 60 THEN 'Under 60s'
                    WHEN duration_seconds < 100 THEN '60-100s'
                    WHEN duration_seconds < 140 THEN '100-140s'
                    ELSE 'Over 140s'
                END AS duration_bucket,
                ROUND(AVG(stars), 2) AS avg_stars,
                ROUND(AVG(destruction_pct), 2) AS avg_destruction,
                COUNT(*) AS total_attacks,
                ROUND(SUM(CASE WHEN stars = 3 THEN 1 ELSE 0 END) * 100.0
                    / COUNT(*), 2) AS three_star_rate
            FROM war_attacks
            WHERE duration_seconds > 0
            GROUP BY duration_bucket
            ORDER BY avg_stars DESC
        """)

    @st.cache_data
    def load_scatter_data():
        return query("""
            SELECT
                duration_seconds,
                destruction_pct,
                stars
            FROM war_attacks
            WHERE duration_seconds > 0
            AND duration_seconds <= 180
            AND destruction_pct > 0
            LIMIT 5000
        """)

    col1, col2 = st.columns(2)

    with col1:
        df_stars = load_stars_data()
        fig_dur1 = px.bar(
            df_stars,
            x='stars',
            y='avg_duration',
            color='avg_destruction',
            title='Average attack duration by stars earned',
            labels={'stars': 'Stars Earned', 'avg_duration': 'Avg Duration (seconds)'},
            color_continuous_scale='RdYlGn',
            text='avg_duration'
        )
        fig_dur1.update_traces(textposition='outside')
        st.plotly_chart(fig_dur1, use_container_width=True)

    with col2:
        df_buckets = load_duration_buckets()
        fig_dur2 = px.bar(
            df_buckets,
            x='duration_bucket',
            y='three_star_rate',
            color='avg_stars',
            title='3-star rate by attack duration bucket',
            labels={'duration_bucket': 'Attack Duration', 'three_star_rate': '3-Star Rate %'},
            color_continuous_scale='RdYlGn',
            text='three_star_rate'
        )
        fig_dur2.update_traces(textposition='outside')
        st.plotly_chart(fig_dur2, use_container_width=True)

    df_scatter = load_scatter_data()
    fig_dur3 = px.scatter(
        df_scatter,
        x='duration_seconds',
        y='destruction_pct',
        color='stars',
        title='Attack duration vs destruction % (sample of 5000 attacks)',
        labels={'duration_seconds': 'Duration (seconds)', 'destruction_pct': 'Destruction %'},
        color_continuous_scale='RdYlGn',
        opacity=0.6
    )
    st.plotly_chart(fig_dur3, use_container_width=True)

    st.info("💡 **Key Insight:** The optimal attack window is 100-140 seconds with 78% 3-star rate. Attacks over 140 seconds suggest players struggling with base complexity. Under 60 seconds indicates rushed or disconnected attacks.")

# ── PAGE 4 — CLAN ANALYSIS ───────────────────────────────────
elif page == "🏆 Clan Analysis":
    st.header("🏆 Clan Analysis")
    st.markdown("*Does clan level predict war wins?*")

    @st.cache_data
    def load_clan_data():
        return query("""
            SELECT
                c.clan_level,
                COUNT(w.war_id) AS total_wars,
                ROUND(SUM(CASE WHEN w.result = 'win' THEN 1 ELSE 0 END) * 100.0
                    / COUNT(w.war_id), 2) AS win_rate_pct,
                ROUND(AVG(w.clan_destruction), 2) AS avg_clan_destruction,
                ROUND(AVG(w.opponent_destruction), 2) AS avg_opponent_destruction,
                SUM(CASE WHEN w.result = 'tie' THEN 1 ELSE 0 END) AS ties
            FROM clans c
            JOIN wars w ON c.clan_tag = w.clan_tag
            WHERE w.result IS NOT NULL
            AND w.clan_destruction <= 100
            AND w.opponent_destruction <= 100
            GROUP BY c.clan_level
            HAVING total_wars > 10
            ORDER BY c.clan_level
        """)

    df_clan = load_clan_data()

    fig5 = px.scatter(
        df_clan,
        x='clan_level',
        y='win_rate_pct',
        size='total_wars',
        color='avg_clan_destruction',
        title='Clan level vs win rate (bubble size = total wars)',
        labels={'clan_level': 'Clan Level', 'win_rate_pct': 'Win Rate %'},
        color_continuous_scale='RdYlGn'
    )
    fig5.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50% baseline")
    st.plotly_chart(fig5, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig6 = px.line(
            df_clan,
            x='clan_level',
            y=['avg_clan_destruction', 'avg_opponent_destruction'],
            title='Clan vs opponent destruction by clan level',
            labels={'clan_level': 'Clan Level', 'value': 'Avg Destruction %'}
        )
        st.plotly_chart(fig6, use_container_width=True)

    with col2:
        fig7 = px.bar(
            df_clan,
            x='clan_level',
            y='ties',
            title='Number of ties by clan level',
            labels={'clan_level': 'Clan Level', 'ties': 'Total Ties'},
            color='ties',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig7, use_container_width=True)

    st.info("💡 **Key Insight:** Clan level is a poor predictor of win rate. Ties dominate at high clan levels — suggesting over-precise matchmaking at elite tiers.")

# ── PAGE 5 — CHURN RISK ──────────────────────────────────────
elif page == "💀 Churn Risk":
    st.header("💀 Churn Risk Analysis")
    st.markdown("*Identifying players at risk of leaving the game*")

    @st.cache_data
    def load_churn_dist():
        return query("""
            SELECT
                CASE
                    WHEN churn_risk_score >= 0.8 THEN 'Critical'
                    WHEN churn_risk_score >= 0.6 THEN 'High'
                    WHEN churn_risk_score >= 0.4 THEN 'Medium'
                    WHEN churn_risk_score >= 0.2 THEN 'Low'
                    ELSE 'Minimal'
                END AS risk_category,
                COUNT(*) AS total_players
            FROM players
            WHERE churn_risk_score IS NOT NULL
            GROUP BY risk_category
            ORDER BY MIN(churn_risk_score) DESC
        """)

    @st.cache_data
    def load_churn_by_th():
        return query("""
            SELECT
                town_hall_level,
                ROUND(AVG(churn_risk_score), 2) AS avg_churn_risk,
                COUNT(*) AS total_players
            FROM players
            WHERE churn_risk_score IS NOT NULL
            AND town_hall_level BETWEEN 8 AND 18
            GROUP BY town_hall_level
            ORDER BY town_hall_level
        """)

    @st.cache_data
    def load_top_churn():
        return query("""
            SELECT name, town_hall_level, trophies, donations,
                   war_preference, league_name, churn_risk_score
            FROM players
            WHERE churn_risk_score IS NOT NULL
            ORDER BY churn_risk_score DESC
            LIMIT 20
        """)

    col1, col2 = st.columns(2)

    with col1:
        df_churn = load_churn_dist()
        fig8 = px.pie(
            df_churn,
            values='total_players',
            names='risk_category',
            title='Churn risk distribution across all players',
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig8, use_container_width=True)

    with col2:
        df_churn_th = load_churn_by_th()
        fig9 = px.bar(
            df_churn_th,
            x='town_hall_level',
            y='avg_churn_risk',
            color='avg_churn_risk',
            title='Average churn risk by Town Hall level',
            labels={'town_hall_level': 'Town Hall Level', 'avg_churn_risk': 'Avg Churn Risk Score'},
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig9, use_container_width=True)

    st.info("💡 **Key Insight:** 43% of players fall into high or critical churn risk. Lower TH players show significantly higher churn risk — early game experience needs improvement.")

    st.subheader("Top 20 highest churn risk players")
    df_top_churn = load_top_churn()
    df_top_churn.index = range(1, len(df_top_churn) + 1)
    st.dataframe(df_top_churn, use_container_width=True)

# ── PAGE 6 — DONATION BEHAVIOR ───────────────────────────────
elif page == "🎯 Donation Behavior":
    st.header("🎯 Donation Behavior")
    st.markdown("*Donation activity as a proxy for player retention*")

    @st.cache_data
    def load_donation_data():
        return query("""
            SELECT
                CASE
                    WHEN donations = 0 THEN 'Inactive (0)'
                    WHEN donations < 500 THEN 'Low (1-499)'
                    WHEN donations < 1500 THEN 'Medium (500-1499)'
                    WHEN donations < 3000 THEN 'High (1500-2999)'
                    ELSE 'Elite (3000+)'
                END AS donation_bucket,
                COUNT(DISTINCT player_tag) AS total_players,
                ROUND(AVG(attack_wins), 2) AS avg_attack_wins,
                ROUND(AVG(war_stars), 2) AS avg_war_stars,
                ROUND(AVG(trophies), 2) AS avg_trophies,
                ROUND(AVG(donations_received), 2) AS avg_donations_received
            FROM players
            GROUP BY donation_bucket
            ORDER BY avg_war_stars DESC
        """)

    df_don = load_donation_data()

    col1, col2 = st.columns(2)

    with col1:
        fig10 = px.bar(
            df_don,
            x='donation_bucket',
            y='avg_war_stars',
            color='avg_trophies',
            title='Donation activity vs average war stars',
            labels={'donation_bucket': 'Donation Level', 'avg_war_stars': 'Avg War Stars'},
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig10, use_container_width=True)

    with col2:
        fig11 = px.bar(
            df_don,
            x='donation_bucket',
            y='avg_trophies',
            color='avg_attack_wins',
            title='Donation activity vs average trophies',
            labels={'donation_bucket': 'Donation Level', 'avg_trophies': 'Avg Trophies'},
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig11, use_container_width=True)

    fig12 = px.bar(
        df_don,
        x='donation_bucket',
        y='total_players',
        color='avg_attack_wins',
        title='Player count per donation tier',
        labels={'donation_bucket': 'Donation Level', 'total_players': 'Total Players'},
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig12, use_container_width=True)

    st.info("💡 **Key Insight:** Elite donors have 10x higher trophies and 70% more war stars than inactive players. 32% of players have zero donations — a critical retention red flag.")
