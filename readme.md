# 🏢 SmartWorks Client Analytics Dashboard

A comprehensive client analytics platform for SmartWorks operations team to generate detailed client insights, service performance reports, and visual analytics.

## 🌟 Features

### 🔐 **Secure Authentication**
- Multi-user login system
- Role-based access control
- Session management
- Secure logout functionality

### 📊 **Comprehensive Analytics**
- **Client Demographics**: Centre location, seat distribution, contract timeline
- **Pricing Analysis**: Per-seat pricing vs centre averages
- **Service Performance**: 6-month ticket trends and resolution patterns
- **SLA Compliance**: Current month SLA performance metrics
- **Issue Analytics**: Top categories, subcategories, and resolution rates
- **Escalation Analysis**: Multi-level escalation tracking

### 📈 **Visual Reports**
- **4 Key Charts**: Monthly trends, issue categories, escalation levels, SLA compliance
- **Interactive Plotly Charts**: Professional visualizations with hover details
- **Responsive Design**: Works on desktop and mobile devices

### 💾 **Export Options**
- **Markdown Reports**: Clean, readable format
- **PDF Reports**: Professional documents with embedded charts
- **JSON Data**: Raw data export for further analysis
- **Chart Images**: Individual chart exports

### 🤖 **AI-Powered Insights**
- Claude AI integration for intelligent report generation
- Contextual analysis and recommendations
- Professional business language
- Actionable insights for operations team

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MySQL Database
- Anthropic API Key
- Streamlit Account (for deployment)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd smartworks-dashboard
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file:
```env
# Database Configuration
DB_HOST=your_mysql_host
DB_NAME=your_database_name
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_PORT=3306

# AI Service
ANTHROPIC_API_KEY=your_anthropic_api_key

# Prompt Files (optional)
PROMPT_FILE_PATH=./prompt.txt
GRAPH_PROMPT_FILE_PATH=./graph_prompt.txt
```

4. **Run the application**
```bash
streamlit run app.py
```

## 🔧 Configuration

### Authentication Setup
Edit the `VALID_USERS` dictionary in `app.py`:

```python
VALID_USERS = {
    "your_username": "your_password",
    "manager": "secure_password",
    "analyst": "another_password"
}
```

**For Production**: Use environment variables
```python
VALID_USERS = {
    os.getenv("SW_ADMIN_USER"): os.getenv("SW_ADMIN_PASS"),
    os.getenv("SW_MANAGER_USER"): os.getenv("SW_MANAGER_PASS")
}
```

### Database Setup
Ensure your MySQL database has these tables:
- `chatbot_portfolio_sheet` - Client demographics and contract info
- `prod_ticketing` - Ticket data with categories, SLA, escalation info

Required columns in `chatbot_portfolio_sheet`:
- `Centre`, `Client_Name`, `Client_Id`, `Client_Move_in`, `Client_Move_out`
- `Stage_Strategy`, `Status`, `Floor`, `seat_[month][year]`, `revenue_[month][year]`

Required columns in `prod_ticketing`:
- `companyName`, `createdAt`, `clientStatus`, `category`, `subCategory`
- `TAT`, `isDueDateBreached`, `escalationLevel`, `escalationStatus`

## 📁 File Structure

```
smartworks-dashboard/
├── app.py                      # Main Streamlit application
├── prompt.txt                  # AI report generation prompt
├── graph_prompt.txt           # Chart generation prompt
├── requirements.txt           # Python dependencies
├── README.md                  # This documentation
├── .env                       # Environment variables (create this)
├── client_data/              # Generated reports and data
│   ├── *.json               # Raw client data
│   ├── *.md                 # Markdown reports
│   ├── *.pdf                # PDF reports
│   └── *.py                 # Generated chart code
└── .streamlit/
    └── secrets.toml          # Streamlit secrets (for cloud deployment)
```

## 🎯 Usage Guide

### 1. **Login**
- Use provided credentials to access the dashboard
- Demo credentials: `smartworks_admin` / `sw2024!`

### 2. **Generate Report**
- Enter exact client company name
- Click "Generate Report" button
- Wait for AI analysis to complete

### 3. **View Results**
- **AI Report**: Comprehensive client analysis
- **Visual Charts**: 4 key analytics charts
- **Download Options**: Markdown and PDF formats

### 4. **Export Data**
- **Markdown**: Clean, editable format
- **PDF**: Professional presentation format
- **JSON**: Raw data for analysis

## 📊 Chart Types

### 1. **Monthly Ticket Trends**
- Line chart showing 6-month ticket patterns
- Total, resolved, and unresolved ticket trends
- Identifies performance improvements or declines

### 2. **Issue Categories Breakdown**
- Horizontal bar chart of top issue categories
- Shows ticket volume and resolution rates
- Helps identify infrastructure needs

### 3. **Escalation Level Distribution**
- Donut chart of escalation patterns
- Multi-level escalation tracking
- Resolution effectiveness by level

### 4. **SLA Compliance Overview**
- Gauge-style or pie chart
- Current month SLA performance
- Color-coded performance indicators

## 🔒 Security Features

- **Session Management**: Secure user sessions
- **Password Protection**: Multi-user authentication
- **Data Access Control**: Role-based permissions
- **Secure Storage**: Encrypted data handling
- **Logout Protection**: Session cleanup

## 🚀 Deployment

### Streamlit Cloud Deployment

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Deploy on Streamlit Cloud**
- Go to [share.streamlit.io](https://share.streamlit.io)
- Connect your GitHub repository
- Set secrets in the Streamlit dashboard

3. **Configure Secrets**
In Streamlit Cloud, add these secrets:
```toml
[secrets]
DB_HOST = "your_mysql_host"
DB_NAME = "your_database_name"
DB_USER = "your_db_username"
DB_PASSWORD = "your_db_password"
DB_PORT = "3306"
ANTHROPIC_API_KEY = "your_anthropic_api_key"
```

### Local Deployment
```bash
streamlit run app.py --server.port 8501
```

## 🛠️ Customization

### Modify AI Prompts
- Edit `prompt.txt` for report structure changes
- Edit `graph_prompt.txt` for chart modifications
- Changes apply immediately without code updates

### Add New Charts
- Modify `graph_prompt.txt` to include additional charts
- Update chart execution code in `app.py`
- Maintain consistent naming (fig1, fig2, etc.)

### Database Schema Changes
- Update SQL queries in `get_client_data()` function
- Modify column mappings for new data fields
- Test with sample data before deployment

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check `.env` file configuration
   - Verify MySQL server is running
   - Confirm network connectivity

2. **AI Service Unavailable**
   - Verify `ANTHROPIC_API_KEY` in environment
   - Check API quota and billing
   - Test API connection independently

3. **Charts Not Displaying**
   - Check browser console for JavaScript errors
   - Verify Plotly version compatibility
   - Clear browser cache

4. **Authentication Issues**
   - Verify username/password combinations
   - Check session state in Streamlit
   - Clear browser cookies

### Debug Mode
Enable debug logging by adding to `.env`:
```env
STREAMLIT_LOGGER_LEVEL=debug
```

## 📞 Support

For technical support or feature requests:
- Create an issue in the GitHub repository
- Contact the SmartWorks IT team
- Check Streamlit documentation for deployment issues

## 📋 Changelog

### Version 1.0.0
- Initial release with authentication
- AI-powered report generation
- 4 key analytics charts
- Markdown and PDF export
- Multi-user support

### Upcoming Features
- Email report delivery
- Scheduled report generation
- Advanced filtering options
- Custom chart builder
- Mobile app version

## 📄 License

This project is proprietary to SmartWorks. All rights reserved.

---

**SmartWorks Client Analytics Dashboard** - Empowering data-driven decisions for better client experiences.