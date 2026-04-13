import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import webbrowser
import os

# Load the dataset
df = pd.read_csv('data_aging_congress.csv')

##Task 1
# Extract the year from the start_date
df['start_year'] = pd.to_datetime(df['start_date']).dt.year

# Calculate the average age for each start year
avg_age = df.groupby('start_year')['age_years'].mean().reset_index()

# Create the plot
plt.figure(figsize=(12, 6))
plt.plot(avg_age['start_year'], avg_age['age_years'], marker='o', linestyle='-', color='b')

# Customize the plot
plt.title('Average Age of US Congress Members Over Time', fontsize=16)
plt.xlabel('Year', fontsize=14)
plt.ylabel('Average Age (Years)', fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()

# Save the plot to an image file
plt.savefig('congress_average_age.png')

## Task 2
import plotly.express as px

# 1. Calculate the percentage of each generation for each Congress
gen_counts = df.groupby(['congress', 'generation']).size().unstack(fill_value=0)
gen_pct = gen_counts.div(gen_counts.sum(axis=1), axis=0) * 100

# Convert index to a column and melt for Plotly
gen_pct = gen_pct.reset_index()
gen_pct_long = gen_pct.melt(id_vars='congress', var_name='generation', value_name='percentage')

# Sort to ensure the slider plays chronologically
gen_pct_long = gen_pct_long.sort_values(by=['congress', 'generation'])

# Create formatted text for the bars so it only adds text if percentage > 2%
gen_pct_long['bar_text'] = gen_pct_long['percentage'].apply(lambda x: f"{x:.1f}%" if x > 2 else "")

# 2. Create the interactive bar chart with a session slider
fig = px.bar(gen_pct_long, x='generation', y='percentage', color='generation',
             animation_frame='congress',
             animation_group='generation',
             text='bar_text',
             range_y=[0, 100],
             title='Generational Composition by Congress Session',
             labels={'congress': 'Congress (Session Number)', 'percentage': 'Percentage of Members (%)', 'generation': 'Generation'},
             color_discrete_sequence=px.colors.qualitative.Set3)

# Add interactivity: clean hover text
fig.update_traces(hovertemplate='<b>Generation:</b> %{x}<br><b>Percentage:</b> %{y:.1f}%<extra></extra>')

# Remove x-axis tick labels and sort the bars/legend from greatest to lowest overall
fig.update_xaxes(showticklabels=False, categoryorder='total descending')



## Task 3: Split Horizontal Bar Plot (Age Pyramids)
import numpy as np

# Map the major party codes (100 = Democrat, 200 = Republican)
df_parties = df[df['party_code'].isin([100, 200])].copy()
df_parties['Party'] = df_parties['party_code'].map({100: 'Democrat', 200: 'Republican'})

# Create age ranges of 5 years (20-24, 25-29, etc.)
bins = range(20, 105, 5)
labels = [f"{i}-{i+4}" for i in range(20, 100, 5)]
df_parties['age_range'] = pd.cut(df_parties['age_years'], bins=bins, labels=labels, right=False)

# Count the number of members in each age bracket
age_dist = df_parties.groupby(['age_range', 'Party'], observed=True).size().reset_index(name='count')

# Make Democrat counts negative to create the "split" butterfly/pyramid effect
age_dist['plot_count'] = age_dist.apply(lambda r: -r['count'] if r['Party'] == 'Democrat' else r['count'], axis=1)

# Ensure age ranges are sorted from bottom to top
age_dist = age_dist.sort_values(by='age_range')

# Create the split horizontal bar plot
fig3 = px.bar(
    age_dist,
    y='age_range',
    x='plot_count',
    color='Party',
    orientation='h',
    barmode='relative',
    hover_data={'count': True, 'plot_count': False, 'Party': False},
    color_discrete_map={'Democrat': '#1f77b4', 'Republican': '#d62728'},
    title='Task 3: Age Distribution by Political Party (Split Plot)',
    labels={'age_range': 'Age Range (Years)', 'plot_count': 'Total Number of Members'}
)

# Format the X-axis so both sides display positive numbers instead of negative
max_val = max(abs(age_dist['plot_count'].min()), age_dist['plot_count'].max())
tick_step = max(500, int((max_val / 4) / 500) * 500)
tick_range = list(range(0, int(max_val) + tick_step, tick_step))
tickvals = [-t for t in tick_range[:0:-1]] + tick_range
ticktext = [str(abs(t)) for t in tickvals]

fig3.update_layout(xaxis=dict(tickmode='array', tickvals=tickvals, ticktext=ticktext))

# Clean hover text to show absolute counts for both sides
fig3.update_traces(hovertemplate='<b>%{y}</b><br>Count: %{customdata[0]}<extra></extra>')

## Task 4: Interactive State-Based Member Table
import plotly.graph_objects as go

# Group members by state and name to find all the sessions they served
agg_funcs = {'party_code': 'first', 'congress': lambda x: sorted(list(set(x)))}
df_members = df.groupby(['state_abbrev', 'bioname'], observed=True).agg(agg_funcs).reset_index()
df_members['Party'] = df_members['party_code'].map({100: 'Democrat', 200: 'Republican'}).fillna('Other')

# Format the sessions into a clean string and count terms
df_members['Sessions Served'] = df_members['congress'].apply(lambda x: f"{min(x)}-{max(x)}" if len(x)>1 else str(x[0]))
df_members['Terms'] = df_members['congress'].apply(len)

# Get sorted unique states
states = sorted(df_members['state_abbrev'].dropna().unique())

fig4 = go.Figure()

# Add one trace (Table) for EVERY state
for state in states:
    state_df = df_members[df_members['state_abbrev'] == state].sort_values(by='Terms', ascending=False)
    
    fig4.add_trace(go.Table(
        header=dict(
            values=["<b>Name</b>", "<b>Party</b>", "<b>Terms Served</b>", "<b>Sessions</b>"],
            fill_color='paleturquoise',
            align='left'
        ),
        cells=dict(
            values=[state_df['bioname'], state_df['Party'], state_df['Terms'], state_df['Sessions Served']],
            fill_color='lavender',
            align='left'
        ),
        visible=(state == states[0])
    ))

# Create dropdown buttons
buttons = []
for i, state in enumerate(states):
    visibility = [False] * len(states)
    visibility[i] = True
    buttons.append(
        dict(
            label=state,
            method="update",
            args=[{"visible": visibility},
                  {"title": f"Task 4: Congress Members from {state}"}]
        )
    )

fig4.update_layout(
    updatemenus=[
        dict(
            direction="down",
            pad={"r": 10, "t": 10},
            showactive=True,
            active=0,
            buttons=buttons,
            x=0.0,
            xanchor="left",
            y=1.15,
            yanchor="top"
        )
    ],
    title=f"Task 4: Congress Members from {states[0]}",
    template="plotly_white"
)

# --- Dashboard Generation ---
print("Generating unified html dashboard...")

# 1. Base64 Encode Matplotlib Plot
buf = BytesIO()
plt.savefig(buf, format="png", bbox_inches="tight")
buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode("utf-8")
img_uri = f"data:image/png;base64,{img_base64}"

# 2. Extract Plotly HTML Strings
plotly_html_2 = fig.to_html(full_html=False, include_plotlyjs='cdn')
plotly_html_3 = fig3.to_html(full_html=False, include_plotlyjs='cdn')
plotly_html_4 = fig4.to_html(full_html=False, include_plotlyjs='cdn')

# 3. Construct the HTML Dashboard Template
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Congress Data Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; margin: 0; padding: 20px; }
        h1 { text-align: center; color: #343a40; margin-bottom: 30px; }
        .tabs { display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; }
        .tab-btn { padding: 10px 20px; font-size: 16px; font-weight: bold; cursor: pointer; background: #e9ecef; border: 1px solid #dee2e6; border-radius: 5px; transition: 0.2s; }
        .tab-btn:hover { background: #ced4da; }
        .tab-btn.active { background: #007bff; color: white; border-color: #007bff; }
        .tab-content { display: none; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        .tab-content.active { display: block; }
        .plot-container { width: 100%; max-width: 1200px; margin: 0 auto; min-height: 500px; }
        img { max-width: 100%; height: auto; }
    </style>
    <script>
        function openTab(event, tabId) {
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            
            const buttons = document.querySelectorAll('.tab-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
            
            window.dispatchEvent(new Event('resize'));
        }
    </script>
</head>
<body>
    <h1>Congress Aging Data Dashboard</h1>
    
    <div class="tabs">
        <button class="tab-btn active" onclick="openTab(event, 'tab1')">Task 1: Average Age</button>
        <button class="tab-btn" onclick="openTab(event, 'tab2')">Task 2: Generations Over Time</button>
        <button class="tab-btn" onclick="openTab(event, 'tab3')">Task 3: Age Distribution</button>
        <button class="tab-btn" onclick="openTab(event, 'tab4')">Task 4: State Map</button>
    </div>
    
    <div id="tab1" class="tab-content active">
        <div class="plot-container">
            <img src="{img_uri}" alt="Average Age Plot">
        </div>
    </div>
    
    <div id="tab2" class="tab-content">
        <div class="plot-container">
            {plotly_html_2}
        </div>
    </div>
    
    <div id="tab3" class="tab-content">
        <div class="plot-container">
            {plotly_html_3}
        </div>
    </div>
    
    <div id="tab4" class="tab-content">
        <div class="plot-container">
            {plotly_html_4}
        </div>
    </div>
</body>
</html>
""".replace("{img_uri}", img_uri).replace("{plotly_html_2}", plotly_html_2).replace("{plotly_html_3}", plotly_html_3).replace("{plotly_html_4}", plotly_html_4)

# 4. Save and Open Dashboard
dashboard_path = os.path.abspath('congress_dashboard.html')
with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Dashboard successfully generated at: {dashboard_path}")
webbrowser.open(f"file://{dashboard_path}")

## Task 4
