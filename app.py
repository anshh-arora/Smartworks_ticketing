
import pandas as pd
import json
import os
import tempfile
from datetime import datetime, timedelta
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from anthropic import Anthropic
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import hashlib
import base64
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import markdown
warnings.filterwarnings('ignore')

# Load environment variables (for local development)
load_dotenv()

# Authentication credentials - updated for Streamlit Cloud deployment
try:
    # Try to use Streamlit secrets first (for cloud deployment)
    VALID_USERS = {
        "smartworks_admin": st.secrets.get("SMARTWORKS_ADMIN_PASSWORD", "sw2024!"),
        "client_manager": st.secrets.get("CLIENT_MANAGER_PASSWORD", "cm2024!"),
        "operations": st.secrets.get("OPERATIONS_PASSWORD", "ops2024!"),
        "ansh.arora1@sworks.co.in": st.secrets.get("ANSH_PASSWORD", "ansh1529")
    }
except Exception:
    # Fallback to environment variables or defaults (for local development)
    VALID_USERS = {
        "smartworks_admin": os.getenv("SMARTWORKS_ADMIN_PASSWORD", "sw2024!"),
        "client_manager": os.getenv("CLIENT_MANAGER_PASSWORD", "cm2024!"),
        "operations": os.getenv("OPERATIONS_PASSWORD", "ops2024!"),
        "ansh.arora1@sworks.co.in": os.getenv("ANSH_PASSWORD", "ansh1529")
    }

# Create data directory that works with Streamlit Cloud
if 'DATA_DIR' not in st.session_state:
    # Use temporary directory for Streamlit Cloud deployment
    try:
        temp_dir = tempfile.mkdtemp()
        st.session_state.DATA_DIR = temp_dir
        DATA_DIR = temp_dir
    except Exception:
        # Fallback for local development
        DATA_DIR = "/tmp/smartworks_client_data"
        st.session_state.DATA_DIR = DATA_DIR
else:
    DATA_DIR = st.session_state.DATA_DIR

# Ensure directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def check_authentication():
    """Handle user authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 SmartWorks Client Analytics Portal")
        st.markdown("### Please login to access client insights")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username in VALID_USERS and VALID_USERS[username] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
        
        st.info("🔹 Demo Credentials: smartworks_admin / sw2024!")
        return False
    
    return True

def logout():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.username = None
    # Clear generated reports
    if 'generated_reports' in st.session_state:
        del st.session_state.generated_reports
    st.rerun()

# Initialize session state for reports and current view
if 'generated_reports' not in st.session_state:
    st.session_state.generated_reports = []

if 'current_report' not in st.session_state:
    st.session_state.current_report = None

# Initialize connections - optimized for Streamlit Cloud
@st.cache_resource
def init_connections():
    connections = {}
    
    # MySQL connection with timeout and retry logic
    try:
        # Connection parameters with timeouts
        connection_config = {
            'connect_timeout': 10,  # 10 seconds connection timeout
            'autocommit': True,
            'raise_on_warnings': True,
            'use_unicode': True,
            'charset': 'utf8mb4',
            'connection_timeout': 10,
            'pool_name': 'smartworks_pool',
            'pool_size': 3,
            'pool_reset_session': True
        }
        
        # Try Streamlit secrets first (for cloud deployment)
        try:
            connection_config.update({
                'host': st.secrets["DB_HOST"],
                'database': st.secrets["DB_NAME"],
                'user': st.secrets["DB_USER"],
                'password': st.secrets["DB_PASSWORD"],
                'port': int(st.secrets.get("DB_PORT", 3306))
            })
        except Exception:
            # Fallback to environment variables (for local development)
            connection_config.update({
                'host': os.getenv('DB_HOST'),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'port': int(os.getenv("DB_PORT", 3306))
            })
        
        # Create connection with timeout
        conn = mysql.connector.connect(**connection_config)
        
        # Test connection with a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        
        connections['mysql'] = conn
        print("✅ Connected to MySQL database")
        
    except mysql.connector.Error as e:
        st.error(f"❌ MySQL Error: {e}")
        print(f"MySQL connection failed: {e}")
        connections['mysql'] = None
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        print(f"Database connection error: {e}")
        connections['mysql'] = None
    
    # Anthropic AI - quick initialization
    try:
        # Try Streamlit secrets first
        try:
            anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            # Fallback to environment variables
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if anthropic_api_key:
            connections['anthropic'] = Anthropic(
                api_key=anthropic_api_key,
                timeout=30.0  # 30 second timeout for API calls
            )
            print("✅ AI service initialized")
        else:
            connections['anthropic'] = None
            st.warning("⚠️ AI service not available - API key missing")
    except Exception as e:
        st.error(f"❌ Error initializing AI service: {e}")
        connections['anthropic'] = None
    
    return connections

# Load enhanced prompt template for SmartWorks
@st.cache_data
def load_smartworks_prompt():
    try:
        # Try to load from file, with fallback to default
        try:
            prompt_path = st.secrets.get("PROMPT_FILE_PATH", "./prompt.txt")
        except Exception:
            prompt_path = os.getenv("PROMPT_FILE_PATH", "./prompt.txt")
        
        with open(prompt_path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not load prompt file, using default: {e}")
        return """
You are a SmartWorks business analyst generating client insights for the SmartWorks team. 
Create a comprehensive report that helps SmartWorks understand their client's experience and service performance.

Based on the client data provided, generate a professional report with this structure:

## 📍 Client Overview
**Client Name: [Client Name]**
[Client Name] is based out of **[Centre Name]** and has taken a total of **[X] seats**, distributed across [floor details]. 
The client moved into the centre on **[move-in date]**, and was scheduled to move out on **[move-out date]**. 
[If applicable: Since this date has passed, the client moved out [X] days ago / is currently active]
This engagement was with a **[new/renewal/expansion] client**. [Additional context about renewal status]

## 💸 Pricing Overview
The **price per seat** for the client was **INR [X]**, while the **average price per seat** across the centre was **INR [Y]**. 
This indicates a **[X]% [premium/discount]** paid by the client, possibly reflecting [reasoning for pricing difference].

## 📈 Ticketing Trends (Last 6 Months)
Analyze the monthly ticket trends and provide insights:
- Total tickets logged over 6 months
- Monthly resolution patterns
- Trend analysis (improving/declining)
- Resolution rate improvements or concerns

## 🛠️ Top Issues Breakdown
The most frequently reported issues in the last 6 months fall into main categories:
* **[Category 1]** ([X] tickets total)
  * [Subcategory]: [resolved] resolved, [unresolved] unresolved
  * [Subcategory]: [resolved] resolved, [unresolved] unresolved
* **[Category 2]** ([X] tickets total)
  * [Subcategory]: [resolved] resolved, [unresolved] unresolved

Provide insights about infrastructure needs, common pain points, and recommendations.

## ⏱️ SLA Performance (Current Month)
In the most recent month, a total of **[X] tickets** were logged. Of these, **[X] were resolved within SLA**, while **[X] breached SLA**. 
This translates to a **[X]% SLA compliance rate**. [Provide assessment and recommendations]

## 🔺 Escalation Analysis
[If escalation data exists, analyze escalation patterns, levels, and resolution effectiveness]

## 🎯 Key Insights & Recommendations
**For SmartWorks Team:**
- Client satisfaction indicators
- Service improvement areas
- Operational efficiency recommendations
- Client retention insights

Use the provided data: {data}

Format with proper markdown, bold key metrics, and provide actionable insights for the SmartWorks operations team.
"""

def load_graph_prompt():
    try:
        # Try to load from file, with fallback to default
        try:
            graph_prompt_path = st.secrets.get("GRAPH_PROMPT_FILE_PATH", "./graph_prompt.txt")
        except Exception:
            graph_prompt_path = os.getenv("GRAPH_PROMPT_FILE_PATH", "./graph_prompt.txt")
        
        with open(graph_prompt_path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not load graph prompt file, using default: {e}")
        return """
Based on the SmartWorks client data, generate Python code to create EXACTLY 4 charts using plotly for client analytics.

Data: {data}

REQUIREMENTS:
Create these 4 charts in order:
1. fig1 - Monthly Ticket Trends (Line chart showing ticket volume and resolution over time)
2. fig2 - Issue Categories Breakdown (Horizontal bar chart for better readability)
3. fig3 - Escalation Level Distribution (Donut chart with colors)
4. fig4 - SLA Compliance Overview (Gauge chart or pie chart)

TECHNICAL REQUIREMENTS:
- Use plotly.express (px) and plotly.graph_objects (go)
- Make charts visually appealing with SmartWorks color scheme
- Include proper error handling for missing data
- Add hover information and proper formatting

RETURN ONLY executable Python code without markdown formatting.
"""

# Convert plotly figure to base64 image
def fig_to_base64(fig):
    """Convert plotly figure to base64 string for embedding in reports"""
    try:
        img_bytes = fig.to_image(format="png", width=800, height=500)
        img_base64 = base64.b64encode(img_bytes).decode()
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"Error converting figure to base64: {e}")
        return None

# Create markdown report with embedded charts
def create_markdown_with_charts(ai_report, charts, client_name):
    """Create enhanced markdown report with embedded chart images"""
    
    # Convert charts to base64 for embedding
    chart_images = {}
    for chart_name, fig in charts.items():
        if fig is not None:
            base64_img = fig_to_base64(fig)
            if base64_img:
                chart_images[chart_name] = base64_img
    
    # Create enhanced markdown content
    markdown_content = f"""# SmartWorks Client Analytics Report

**Generated on:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  
**Generated by:** {st.session_state.get('username', 'SmartWorks User')}  
**Client:** {client_name}

---

{ai_report}

---

## 📊 Visual Analytics

"""
    
    # Add charts with descriptions
    chart_descriptions = {
        'fig1': '### 📈 Monthly Ticket Trends\nThis chart shows the ticket volume and resolution patterns over the last 6 months, helping identify performance trends.',
        'fig2': '### 🛠️ Issue Categories Breakdown\nAnalysis of the most common issue types, ranked by frequency to identify areas needing attention.',
        'fig3': '### 🔺 Escalation Level Distribution\nBreakdown of tickets by escalation level, showing the complexity and severity of issues.',
        'fig4': '### ⏱️ SLA Compliance Overview\nCurrent month SLA performance metrics, indicating service quality and responsiveness.'
    }
    
    # Add each chart with description
    for chart_key in ['fig1', 'fig2', 'fig3', 'fig4']:
        if chart_key in chart_images:
            markdown_content += f"\n{chart_descriptions.get(chart_key, '')}\n\n"
            markdown_content += f"![{chart_key}]({chart_images[chart_key]})\n\n"
    
    markdown_content += f"""
---

## 📋 Report Summary

This comprehensive analysis provides SmartWorks operations team with:
- **Client demographic and contract insights**
- **6-month service performance trends**
- **Current SLA compliance metrics**
- **Issue category analysis with resolution patterns**
- **Escalation effectiveness assessment**
- **Actionable recommendations for service improvement**

**Next Steps:**
1. Review identified areas for improvement
2. Implement recommended process changes
3. Monitor progress against established benchmarks
4. Schedule follow-up analysis in 30 days

---

*Report generated by SmartWorks Client Analytics Dashboard*  
*For questions or additional analysis, contact the SmartWorks operations team*
"""
    
    return markdown_content

# Create PDF report
def create_pdf_report(ai_report, charts, client_name):
    """Create PDF report with embedded charts"""
    try:
        # Create BytesIO buffer for PDF
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Title page
        story.append(Paragraph("SmartWorks Client Analytics Report", title_style))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Client:</b> {client_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated on:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated by:</b> {st.session_state.get('username', 'SmartWorks User')}", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Add AI report content
        # Convert markdown to HTML for better formatting
        report_lines = ai_report.split('\n')
        for line in report_lines:
            if line.strip():
                if line.startswith('##'):
                    story.append(Paragraph(line.replace('##', '').strip(), heading_style))
                elif line.startswith('**') and line.endswith('**'):
                    story.append(Paragraph(f"<b>{line.strip('*')}</b>", styles['Normal']))
                else:
                    story.append(Paragraph(line, styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Add page break before charts
        story.append(PageBreak())
        story.append(Paragraph("Visual Analytics", title_style))
        story.append(Spacer(1, 20))
        
        # Add charts
        chart_titles = {
            'fig1': 'Monthly Ticket Trends',
            'fig2': 'Issue Categories Breakdown', 
            'fig3': 'Escalation Level Distribution',
            'fig4': 'SLA Compliance Overview'
        }
        
        for chart_key in ['fig1', 'fig2', 'fig3', 'fig4']:
            if chart_key in charts and charts[chart_key] is not None:
                # Add chart title
                story.append(Paragraph(chart_titles.get(chart_key, chart_key), heading_style))
                story.append(Spacer(1, 12))
                
                # Convert chart to image
                img_bytes = charts[chart_key].to_image(format="png", width=600, height=400)
                img = Image(io.BytesIO(img_bytes), width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None

# Execute SQL query with logging
def execute_query(cursor, query, query_name=""):
    try:
        print(f"\n🔍 Executing {query_name}:")
        print("-" * 50)
        print(query)
        print("-" * 50)
        
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df_result = pd.DataFrame(result, columns=columns).to_dict(orient='records')
        
        print(f"✅ {query_name}: {len(df_result)} records found")
        return df_result
    except Error as e:
        print(f"❌ Error executing {query_name}: {e}")
        st.error(f"Error executing {query_name}: {e}")
        return []

# Get client data with enhanced queries
def get_client_data(client_name, cursor):
    current_year = pd.Timestamp.now().year
    current_month = pd.Timestamp.now().month
    
    month_names = {
        1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'may', 6: 'jun',
        7: 'jul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
    }
    current_month_name = month_names[current_month]
    
    seat_column = f"seat_{current_month_name}{current_year}"
    revenue_column = f"revenue_{current_month_name}{current_year}"
    
    print(f"\n📅 Analysis Period: {current_month_name.upper()} {current_year}")
    print(f"📊 Using columns: {seat_column}, {revenue_column}")
    
    queries = {
        "client_demographics": f"""
        SELECT 
            Centre as centre_name,
            Client_Name as client_name,
            Client_Id as client_id,
            Client_Move_in as move_in_date,
            Client_Move_out as move_out_date,
            Stage_Strategy as client_type,
            Status,
            Floor as floor_info,
            COALESCE({seat_column}, 0) as current_month_seats,
            COALESCE({revenue_column}, 0) as current_month_revenue,
            CASE 
                WHEN COALESCE({seat_column}, 0) > 0 AND COALESCE({revenue_column}, 0) > 0 THEN 
                    ROUND(COALESCE({revenue_column}, 0) / COALESCE({seat_column}, 1), 2)
                ELSE 0 
            END as current_month_price_per_seat,
            Escalation,
            Escalation_Frequency,
            First_Escalation_Date,
            CASE 
                WHEN Client_Move_out < CURDATE() THEN 
                    DATEDIFF(CURDATE(), Client_Move_out)
                ELSE 0 
            END as days_since_moveout
        FROM chatbot_portfolio_sheet
        WHERE Status IN ('Active', 'Inactive') AND Client_Name = '{client_name}'
        """,
        
        "center_avg_pricing": f"""
        SELECT 
            p.Centre,
            COUNT(*) as total_clients_in_center,
            SUM(COALESCE({seat_column}, 0)) as total_center_seats,
            SUM(COALESCE({revenue_column}, 0)) as total_center_revenue,
            ROUND(AVG(
                CASE 
                    WHEN COALESCE({seat_column}, 0) > 0 AND COALESCE({revenue_column}, 0) > 0 THEN 
                        COALESCE({revenue_column}, 0) / COALESCE({seat_column}, 1)
                    ELSE NULL 
                END
            ), 2) as center_avg_price_per_seat
        FROM chatbot_portfolio_sheet p
        WHERE p.Status = 'Active'
            AND COALESCE({seat_column}, 0) > 0
            AND COALESCE({revenue_column}, 0) > 0
            AND p.Centre = (
                SELECT Centre 
                FROM chatbot_portfolio_sheet 
                WHERE Client_Name = '{client_name}' 
                LIMIT 1
            )
        GROUP BY p.Centre
        """,
        
        "monthly_trend": f"""
        SELECT 
            DATE_FORMAT(createdAt, '%Y-%m') as month,
            COUNT(CASE WHEN clientStatus = 'Closed' THEN 1 END) as resolved_tickets,
            COUNT(CASE WHEN clientStatus = 'Open' THEN 1 END) as unresolved_tickets,
            COUNT(*) as total_tickets,
            ROUND(AVG(CASE WHEN clientStatus = 'Closed' AND TAT IS NOT NULL THEN TAT END), 2) as avg_tat
        FROM prod_ticketing 
        WHERE companyName = '{client_name}'
            AND createdAt >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(createdAt, '%Y-%m')
        ORDER BY month
        """,
        
        "issues_breakdown": f"""
        SELECT 
            category,
            subCategory,
            COUNT(CASE WHEN clientStatus = 'Closed' THEN 1 END) as resolved_count,
            COUNT(CASE WHEN clientStatus = 'Open' THEN 1 END) as unresolved_count,
            COUNT(*) as total_tickets,
            ROUND(AVG(CASE WHEN clientStatus = 'Closed' AND TAT IS NOT NULL THEN TAT END), 2) as avg_tat,
            ROUND((COUNT(CASE WHEN clientStatus = 'Closed' THEN 1 END) * 100.0 / COUNT(*)), 2) as resolution_rate
        FROM prod_ticketing 
        WHERE companyName = '{client_name}'
            AND createdAt >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            AND category IS NOT NULL
            AND category != 'AC'
        GROUP BY category, subCategory
        ORDER BY total_tickets DESC
        """,
        
        "sla_compliance": f"""
        SELECT 
            COUNT(*) as total_tickets,
            COUNT(CASE WHEN isDueDateBreached = 0 THEN 1 END) as within_sla,
            COUNT(CASE WHEN isDueDateBreached = 1 THEN 1 END) as sla_breached,
            ROUND((COUNT(CASE WHEN isDueDateBreached = 0 THEN 1 END) * 100.0 / COUNT(*)), 2) as sla_compliance_rate,
            ROUND(AVG(CASE WHEN isDueDateBreached = 0 AND TAT IS NOT NULL THEN TAT END), 2) as avg_tat_within_sla,
            ROUND(AVG(CASE WHEN isDueDateBreached = 1 AND TAT IS NOT NULL THEN TAT END), 2) as avg_tat_breached
        FROM prod_ticketing 
        WHERE companyName = '{client_name}'
            AND YEAR(createdAt) = {current_year}
            AND MONTH(createdAt) = {current_month}
        """,
        
        "escalation_analysis": f"""
        SELECT 
            escalationLevel,
            escalationStatus,
            COUNT(*) as ticket_count,
            ROUND(AVG(TAT), 2) as avg_resolution_time,
            COUNT(CASE WHEN clientStatus = 'Closed' THEN 1 END) as resolved_count,
            COUNT(CASE WHEN clientStatus = 'Open' THEN 1 END) as unresolved_count,
            ROUND((COUNT(CASE WHEN clientStatus = 'Closed' THEN 1 END) * 100.0 / COUNT(*)), 2) as resolution_rate
        FROM prod_ticketing 
        WHERE companyName = '{client_name}'
            AND createdAt >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            AND escalationLevel IS NOT NULL
        GROUP BY escalationLevel, escalationStatus
        ORDER BY escalationLevel
        """
    }
    
    data = {}
    for query_name, query in queries.items():
        try:
            result = execute_query(cursor, query, query_name)
            data[query_name] = result
        except Exception as e:
            print(f"❌ Error executing {query_name}: {e}")
            data[query_name] = []
    
    return data

# Generate AI report 
def generate_smartworks_report(ai_client, data):
    try:
        prompt = load_smartworks_prompt()
        formatted_prompt = prompt.replace("{data}", json.dumps(data, indent=2, default=str))
        
        response = ai_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=6000,
            temperature=0.2,
            messages=[{"role": "user", "content": formatted_prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        st.error(f"Error generating report: {e}")
        return None

# Generate chart code
def generate_chart_code_with_ai(ai_client, data):
    try:
        chart_prompt = load_graph_prompt()
        formatted_prompt = chart_prompt.replace("{data}", json.dumps(data, indent=2, default=str))
        
        response = ai_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.1,
            messages=[{"role": "user", "content": formatted_prompt}]
        )
        
        chart_code = response.content[0].text
        
        # Clean up code
        if "```python" in chart_code:
            chart_code = chart_code.split("```python")[1].split("```")[0]
        elif "```" in chart_code:
            chart_code = chart_code.split("```")[1].split("```")[0]
        
        return chart_code.strip()
    except Exception as e:
        st.error(f"Error generating chart code: {e}")
        return None

# Execute chart code
def execute_chart_code(chart_code, client_data):
    charts = {}
    
    try:
        exec_globals = {
            'pd': pd,
            'px': px,
            'go': go,
            'make_subplots': make_subplots,
            'client_data': client_data
        }
        
        exec(chart_code, exec_globals)
        
        for key, value in exec_globals.items():
            if key.startswith('fig') and hasattr(value, 'show'):
                charts[key] = value
                
        return charts
        
    except Exception as e:
        st.error(f"Error executing chart code: {e}")
        return {}

# Save data function - updated for Streamlit Cloud
def save_client_data(client_name, data):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{client_name.replace(' ', '_').replace(',', '')}_{timestamp}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        data_with_meta = {
            "client_name": client_name,
            "timestamp": timestamp,
            "generated_at": datetime.now().isoformat(),
            "generated_by": st.session_state.get('username', 'unknown'),
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_with_meta, f, indent=2, default=str, ensure_ascii=False)
        return filepath
    except Exception as e:
        print(f"Warning: Could not save data: {e}")
        return None

# Display previous reports section
def display_previous_reports():
    """Display previously generated reports in sidebar"""
    if st.session_state.generated_reports:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📋 Recent Reports")
        
        for i, report in enumerate(st.session_state.generated_reports[:5]):  # Show only last 5
            with st.sidebar.expander(f"📊 {report['client_name']}", expanded=False):
                st.markdown(f"**Generated:** {report['timestamp']}")
                st.markdown(f"**By:** {report['generated_by']}")
                
                # View report button
                if st.button(f"👁️ View Report", key=f"view_{i}"):
                    st.session_state.current_report = report
                    st.rerun()
                
                # Download buttons for each report
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📄 MD",
                        data=report['markdown_content'],
                        file_name=f"{report['client_name']}_Report.md",
                        mime="text/markdown",
                        key=f"md_download_{i}",
                        use_container_width=True
                    )
                
                with col2:
                    if report['pdf_content']:
                        st.download_button(
                            label="📕 PDF",
                            data=report['pdf_content'],
                            file_name=f"{report['client_name']}_Report.pdf",
                            mime="application/pdf",
                            key=f"pdf_download_{i}",
                            use_container_width=True
                        )

# Simulate streaming text effect for better user experience
def stream_text(text, container):
    """Simulate streaming text like ChatGPT"""
    words = text.split()
    displayed_text = ""
    
    for i, word in enumerate(words):
        displayed_text += word + " "
        container.markdown(displayed_text)
        
        # Add small delay for streaming effect (only for first few words)
        if i < 20:  # Stream first 20 words slower
            import time
            time.sleep(0.05)
    
    return displayed_text

# Show elegant loading messages with spinner
def show_loading_steps(step_num, total_steps, message):
    """Show elegant loading progress with messages and spinner"""
    progress = step_num / total_steps
    
    loading_messages = {
        1: "🔍 **Analyzing client data...**\n\n*Gathering comprehensive insights from your database*",
        2: "🤖 **Generating AI insights...**\n\n*Processing patterns and trends with advanced analytics*", 
        3: "📊 **Creating visualizations...**\n\n*Building interactive charts for better understanding*",
        4: "📝 **Finalizing report...**\n\n*Preparing professional-grade analysis document*"
    }
    
    # Create columns for progress bar and spinner
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.progress(progress)
        st.markdown(loading_messages.get(step_num, message))
    
    with col2:
        # Add spinner with different emojis for each step
        spinner_icons = {
            1: "🔄",
            2: "⚡", 
            3: "📈",
            4: "✨"
        }
        
        with st.spinner(f"{spinner_icons.get(step_num, '⏳')} Processing..."):
            import time
            time.sleep(0.5)  # Small delay to show spinner
    
    return progress

# Main Streamlit App
def main():
    st.set_page_config(
        page_title="SmartWorks Client Analytics", 
        page_icon="🏢", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check authentication first
    if not check_authentication():
        return
    
    # Sidebar with user info and navigation
    with st.sidebar:
        st.title("🏢 SmartWorks")
        st.markdown(f"**Welcome, {st.session_state.username}!**")
        
        st.markdown("---")
        st.markdown("### 📊 Client Analytics Portal")
        st.markdown("Generate comprehensive client insights and service performance reports")
        
        # Display previous reports
        display_previous_reports()
        
        st.markdown("---")
        if st.button("🚪 Logout"):
            logout()
    
    # Main content
    st.title("🏢 SmartWorks Client Analytics Dashboard")
    st.markdown("**Comprehensive client insights for the SmartWorks operations team**")
    
    # Initialize connections
    connections = init_connections()
    
    # Client search section
    st.header("🔍 Client Analysis")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        client_name = st.text_input(
            "Enter client company name:",
            placeholder="e.g., Zomato, Swiggy, Flipkart",
            help="Enter the exact company name as registered in SmartWorks system"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("🚀 Generate Report", type="primary", use_container_width=True)
    
    # Analysis period info
    current_date = pd.Timestamp.now()
    st.info(f"📅 **Analysis Period:** {current_date.strftime('%B %Y')} | **Trend Data:** Last 6 months")
    
    # Display current/previous report if exists
    if st.session_state.current_report:
        st.markdown("---")
        st.header(f"📊 Report: {st.session_state.current_report['client_name']}")
        
        # Show the AI report
        st.markdown(st.session_state.current_report.get('ai_report', ''))
        
        # Show charts if available
        if st.session_state.current_report.get('charts'):
            st.markdown("---")
            st.header("📊 Visual Analytics")
            
            charts = st.session_state.current_report['charts']
            chart_list = list(charts.items())
            
            if len(chart_list) >= 2:
                col1, col2 = st.columns(2)
                with col1:
                    if 'fig1' in dict(chart_list):
                        st.plotly_chart(dict(chart_list)['fig1'], use_container_width=True)
                with col2:
                    if 'fig2' in dict(chart_list):
                        st.plotly_chart(dict(chart_list)['fig2'], use_container_width=True)
            
            if len(chart_list) >= 4:
                col3, col4 = st.columns(2)
                with col3:
                    if 'fig3' in dict(chart_list):
                        st.plotly_chart(dict(chart_list)['fig3'], use_container_width=True)
                with col4:
                    if 'fig4' in dict(chart_list):
                        st.plotly_chart(dict(chart_list)['fig4'], use_container_width=True)
        
        # Download section for current report
        st.markdown("---")
        st.header("📥 Download This Report")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.download_button(
                label="📄 Download Markdown",
                data=st.session_state.current_report['markdown_content'],
                file_name=f"SmartWorks_{st.session_state.current_report['client_name'].replace(' ', '_')}_Report.md",
                mime="text/markdown",
                help="Complete report with embedded charts",
                use_container_width=True
            )
        
        with col2:
            if st.session_state.current_report.get('pdf_content'):
                st.download_button(
                    label="📕 Download PDF",
                    data=st.session_state.current_report['pdf_content'],
                    file_name=f"SmartWorks_{st.session_state.current_report['client_name'].replace(' ', '_')}_Report.pdf",
                    mime="application/pdf",
                    help="Professional PDF with charts",
                    use_container_width=True
                )
        
        with col3:
            if st.button("🔄 Generate New Report", use_container_width=True):
                st.session_state.current_report = None
                st.rerun()
        
        st.markdown("---")
    
    if generate_btn:
        if not client_name.strip():
            st.error("Please enter a client name.")
            return
        
        if not connections['mysql']:
            st.error("❌ **Database connection unavailable**\n\nPlease contact IT support to resolve connectivity issues.")
            return
        
        # Clear current report to show new one
        st.session_state.current_report = None
        
        # Enhanced loading experience
        with st.container():
            st.markdown("### 🚀 Generating Client Analysis")
            loading_container = st.empty()
            progress_container = st.empty()
        
        try:
            # Step 1: Fetch data (silent in background)
            with progress_container:
                show_loading_steps(1, 4, "Analyzing client data...")
            
            cursor = connections['mysql'].cursor()
            data = get_client_data(client_name, cursor)
            
            # Step 2: Validate data
            has_demographics = data.get('client_demographics') and len(data['client_demographics']) > 0
            has_tickets = data.get('monthly_trend') and len(data['monthly_trend']) > 0
            
            if not has_demographics and not has_tickets:
                loading_container.empty()
                progress_container.empty()
                st.error(f"❌ **Client '{client_name}' not found**\n\nPlease check the spelling and try again.")
                return
            elif not has_demographics:
                st.warning("⚠️ **Limited data available** - Client found in ticketing system only")
            elif not has_tickets:
                st.warning("⚠️ **Limited analytics** - No recent tickets found for this client")
            
            # Step 3: Generate AI report
            if connections['anthropic']:
                with progress_container:
                    show_loading_steps(2, 4, "Generating AI insights...")
                
                ai_report = generate_smartworks_report(connections['anthropic'], data)
                
                if ai_report:
                    # Step 4: Generate charts
                    with progress_container:
                        show_loading_steps(3, 4, "Creating visualizations...")
                    
                    chart_code = generate_chart_code_with_ai(connections['anthropic'], data)
                    charts = {}
                    
                    if chart_code:
                        charts = execute_chart_code(chart_code, data)
                    
                    # Step 5: Finalize
                    with progress_container:
                        show_loading_steps(4, 4, "Finalizing report...")
                    
                    # Save data quietly in background
                    save_client_data(client_name, data)
                    
                    # Create download content
                    markdown_content = create_markdown_with_charts(ai_report, charts, client_name)
                    pdf_content = create_pdf_report(ai_report, charts, client_name) if charts else None
                    
                    # Store in session state
                    report_data = {
                        'client_name': client_name,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'generated_by': st.session_state.get('username', 'Unknown'),
                        'ai_report': ai_report,
                        'charts': charts,
                        'markdown_content': markdown_content,
                        'pdf_content': pdf_content
                    }
                    
                    # Add to reports list and set as current
                    st.session_state.generated_reports.insert(0, report_data)
                    st.session_state.current_report = report_data
                    
                    # Keep only last 10 reports
                    if len(st.session_state.generated_reports) > 10:
                        st.session_state.generated_reports = st.session_state.generated_reports[:10]
                    
                    # Clear loading and show success
                    loading_container.empty()
                    progress_container.empty()
                    
                    with st.container():
                        st.success("✅ **Analysis Complete!** Your comprehensive client report is ready.")
                        st.balloons()  # Celebratory effect
                    
                    # Rerun to show the report
                    st.rerun()
                
                else:
                    loading_container.empty()
                    progress_container.empty()
                    st.error("❌ **Report generation failed**\n\nPlease try again or contact support.")
            
            else:
                loading_container.empty()
                progress_container.empty()
                st.error("❌ **AI service unavailable**\n\nPlease contact IT support to enable AI analysis.")
                
        except Exception as e:
            loading_container.empty()
            progress_container.empty()
            st.error(f"❌ **Analysis failed**\n\n{str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()

if __name__ == "__main__":
    main()