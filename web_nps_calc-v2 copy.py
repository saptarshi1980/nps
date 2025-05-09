import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from fpdf import FPDF
import io
import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
from functools import lru_cache

# Function to convert number to words
def number_to_words_indian(num):
    """Convert a number to Indian number system words with rupees"""
    if num == 0:
        return "Zero Rupees"
    
    # Handling lakhs and crores in Indian system
    def get_words(n):
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", 
                "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        if n < 20:
            return units[n]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
        elif n < 1000:
            return units[n // 100] + " Hundred" + (" and " + get_words(n % 100) if n % 100 != 0 else "")
        elif n < 100000:
            return get_words(n // 1000) + " Thousand" + (" " + get_words(n % 1000) if n % 1000 != 0 else "")
        elif n < 10000000:
            return get_words(n // 100000) + " Lakh" + (" " + get_words(n % 100000) if n % 100000 != 0 else "")
        else:
            return get_words(n // 10000000) + " Crore" + (" " + get_words(n % 10000000) if n % 10000000 != 0 else "")
    
    # Handle decimal part
    int_part = int(num)
    decimal_part = int((num - int_part) * 100)
    
    result = get_words(int_part) + " Rupees"
    if decimal_part > 0:
        result += " and " + get_words(decimal_part) + " Paise"
    
    return result

class NPSCalculator:
    def __init__(self, birth_date, current_balance, monthly_contribution, annuity_ratio, 
                 annual_return_rate, annual_increase_rate=0.0, retirement_age=60, annuity_rate=0.06):
        self.birth_date = birth_date
        self.current_date = datetime.date.today()
        self.current_age = self.calculate_exact_age()
        self.current_balance = current_balance
        self.monthly_contribution = monthly_contribution
        self.annuity_ratio = annuity_ratio
        self.annual_return_rate = annual_return_rate
        self.annual_increase_rate = annual_increase_rate
        self.retirement_age = retirement_age
        self.annuity_rate = annuity_rate
        
        # Use numpy arrays for better performance
        self.yearly_data = []
        self.monthly_data = []
        
        # Compute results
        self.compute()

    def calculate_exact_age(self):
        return relativedelta(self.current_date, self.birth_date).years

    @lru_cache(maxsize=1)  # Cache the compute results for performance
    def compute(self):
        # Calculate retirement date as last day of birth month in retirement year
        retirement_year = self.birth_date.year + self.retirement_age
        retirement_month = self.birth_date.month
        
        # Get last day of retirement month
        if retirement_month == 12:
            next_month = 1
            next_year = retirement_year + 1
        else:
            next_month = retirement_month + 1
            next_year = retirement_year
        
        retirement_date = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
        
        months_to_retirement = (retirement_date.year - self.current_date.year) * 12 + (retirement_date.month - self.current_date.month)
        
        if months_to_retirement <= 0:
            raise ValueError("You have already reached or passed retirement age")
        
        self.months = months_to_retirement
        self.years = months_to_retirement / 12
        self.monthly_rate = self.annual_return_rate / 12

        # Pre-allocate arrays for better performance
        corpus_values = np.zeros(months_to_retirement + 1)
        corpus_values[0] = self.current_balance
        
        # Use vectorized operations where possible
        monthly = self.monthly_contribution
        current_date = self.current_date
        
        # More efficient calculation using numpy for the corpus growth
        for month in range(1, months_to_retirement + 1):
            corpus_values[month] = corpus_values[month-1] * (1 + self.monthly_rate) + monthly
            current_date += relativedelta(months=1)
            
            # Only store essential data points to reduce memory usage
            if month % 3 == 0 or month == months_to_retirement:  # Store quarterly data points
                self.monthly_data.append((current_date, corpus_values[month]))
            
            # Record yearly data (at end of each year)
            if month % 12 == 0 or month == months_to_retirement:
                self.yearly_data.append((current_date, corpus_values[month]))
            
            # Increase contribution annually (on the anniversary)
            if month % 12 == 0:
                monthly *= (1 + self.annual_increase_rate)

        self.total_corpus = corpus_values[-1]
        self.retirement_date = retirement_date

        self.annuity_corpus = self.total_corpus * self.annuity_ratio
        self.lump_sum = self.total_corpus * (1 - self.annuity_ratio)
        self.monthly_pension = (self.annuity_corpus * self.annuity_rate) / 12

        # Calculate total invested amount more efficiently
        self.total_invested = self.current_balance
        
        # Use arithmetic series formula for calculating total contribution
        if self.annual_increase_rate == 0:
            # Simple arithmetic series when no increase
            self.total_invested += self.monthly_contribution * months_to_retirement
        else:
            # For geometric series with increasing contributions
            monthly = self.monthly_contribution
            for year in range(int(self.years)):
                self.total_invested += monthly * 12
                monthly *= (1 + self.annual_increase_rate)
            
            # Add partial year investments if retirement doesn't fall on year boundary
            if months_to_retirement % 12 != 0:
                self.total_invested += monthly * (months_to_retirement % 12)
        
        self.growth = self.total_corpus - self.total_invested
        
        # Generate word representations
        self.total_corpus_words = number_to_words_indian(self.total_corpus)
        self.annuity_corpus_words = number_to_words_indian(self.annuity_corpus)
        self.lump_sum_words = number_to_words_indian(self.lump_sum)
        self.monthly_pension_words = number_to_words_indian(self.monthly_pension)
        self.total_invested_words = number_to_words_indian(self.total_invested)
        self.growth_words = number_to_words_indian(self.growth)

    def generate_bar_chart(self):
        fig, ax = plt.subplots(figsize=(6, 2.5))
        categories = ["Total Invested", "Growth", "Total Corpus", "Monthly Pension"]
        values = [self.total_invested, self.growth, self.total_corpus, self.monthly_pension]
        colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]

        bars = ax.bar(categories, values, color=colors, width=0.6)
        
        # Format y-axis to show full rupees amount without thousand separators
        ax.yaxis.set_major_formatter(lambda x, pos: f'₹{x:.0f}')
        
        # Add value labels without thousand separators
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, 
                f'₹{height:.0f}', 
                ha='center', va='bottom', 
                fontsize=6)
        
        plt.title("Investment Growth vs Monthly Pension", fontsize=9)
        plt.ylabel("Amount (₹)", fontsize=7)
        ax.tick_params(axis='x', labelsize=6, rotation=15)
        ax.tick_params(axis='y', labelsize=6)
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(pad=0.8)
        return fig
    
    def generate_pie_chart(self):
        fig, ax = plt.subplots(figsize=(4, 3))
        sizes = [self.lump_sum, self.annuity_corpus]
        
        # Format large numbers for better readability
        def format_amount(val):
            if val >= 1e7:  # Above 1 crore
                return f"Rs.{val/1e7:.2f} Cr"
            elif val >= 1e5:  # Above 1 lakh
                return f"Rs.{val/1e5:.2f} L"
            else:
                return f"Rs.{val:.0f}"
        
        labels = [f"Lump Sum: {format_amount(self.lump_sum)}", 
                  f"Annuity: {format_amount(self.annuity_corpus)}"]
        
        ax.pie(sizes, labels=None,
               autopct=lambda p: f'{p:.1f}%',
               colors=["#e377c2", "#8c564b"],
               wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
        plt.title("Corpus Distribution", fontsize=10)
        
        # Add legend with better position
        ax.legend(labels, loc="center left", bbox_to_anchor=(0.9, 0.5), fontsize=7)
        
        # Add monthly pension as text annotation
        ax.annotate(f"Monthly Pension (Consedering Annuity Rate of 6%): {format_amount(self.monthly_pension)}", 
                   xy=(0.5, -0.1), xycoords='axes fraction',
                   ha='center', va='center', fontsize=7)
        
        plt.tight_layout()
        return fig

    def generate_line_chart(self):
        # Use less data points for smoother rendering
        dates, values = zip(*self.yearly_data)
        
        fig, ax = plt.subplots(figsize=(6, 3))
        
        # Use a more efficient line rendering
        ax.plot(dates, values, marker='o', markersize=3,
                linestyle='-', linewidth=1,
                color='#1f77b4', label='Yearly Corpus')
        
        # Display only quarterly data points for better performance
        m_dates, m_values = zip(*self.monthly_data)
        ax.plot(m_dates, m_values, linestyle='-', linewidth=0.5, 
                color='#1f77b4', alpha=0.3, label='Quarterly Progress')
        
        ax.set_title("NPS Corpus Growth Over Time", fontsize=10)
        ax.set_xlabel("Year", fontsize=8)
        ax.set_ylabel("Corpus Value (Rs.)", fontsize=8)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Move legend to better position
        ax.legend(fontsize=7, loc='upper left')
        
        # Format y-axis with simplified notation for large numbers
        def format_func(x, pos):
            if x >= 1e7:
                return f'Rs.{x/1e7:.1f}Cr'
            elif x >= 1e5:
                return f'Rs.{x/1e5:.1f}L'
            else:
                return f'Rs.{x:.0f}'
                
        ax.yaxis.set_major_formatter(plt.FuncFormatter(format_func))
        
        # Optimize x-axis labels to show fewer points for clarity
        if len(dates) > 10:
            plt.xticks([dates[0], dates[-1]] + [dates[i] for i in range(1, len(dates)-1, len(dates)//5)], 
                      rotation=45, fontsize=7)
        else:
            plt.xticks(rotation=45, fontsize=7)
            
        plt.yticks(fontsize=7)
        plt.tight_layout(pad=1.0)
        return fig
    
    def generate_detailed_table(self, show_all_years=True):
        table_data = []
        
        if show_all_years:
            # Show all years when show_all_years is True
            for date, value in self.yearly_data:
                years_contributed = date.year - self.current_date.year
                current_monthly_contribution = self.monthly_contribution * (1 + self.annual_increase_rate) ** years_contributed
                
                # Format large numbers
                if value >= 1e7:  # Above 1 crore
                    formatted_value = f"₹{value/1e7:.2f} Cr"
                elif value >= 1e5:  # Above 1 lakh
                    formatted_value = f"₹{value/1e5:.2f} L"
                else:
                    formatted_value = f"₹{value:.2f}"
                    
                table_data.append({
                    "Year": date.year,
                    "Age": self.current_age + years_contributed,
                    "Corpus Value": formatted_value,
                    "Monthly Contribution": f"₹{current_monthly_contribution:.2f}"
                })
        else:
            # Show only approximately 10 data points when show_all_years is False
            step = max(1, len(self.yearly_data) // 10)
            
            for i in range(0, len(self.yearly_data), step):
                date, value = self.yearly_data[i]
                years_contributed = date.year - self.current_date.year
                current_monthly_contribution = self.monthly_contribution * (1 + self.annual_increase_rate) ** years_contributed
                
                # Format large numbers
                if value >= 1e7:  # Above 1 crore
                    formatted_value = f"₹{value/1e7:.2f} Cr"
                elif value >= 1e5:  # Above 1 lakh
                    formatted_value = f"₹{value/1e5:.2f} L"
                else:
                    formatted_value = f"₹{value:.2f}"
                    
                table_data.append({
                    "Year": date.year,
                    "Age": self.current_age + years_contributed,
                    "Corpus Value": formatted_value,
                    "Monthly Contribution": f"₹{current_monthly_contribution:.2f}"
                })
                
            # Always include the final year if it's not already included
            if len(self.yearly_data) > 0 and (len(self.yearly_data)-1) % step != 0:
                date, value = self.yearly_data[-1]
                years_contributed = date.year - self.current_date.year
                current_monthly_contribution = self.monthly_contribution * (1 + self.annual_increase_rate) ** years_contributed
                
                if value >= 1e7:
                    formatted_value = f"₹{value/1e7:.2f} Cr"
                elif value >= 1e5:
                    formatted_value = f"₹{value/1e5:.2f} L"
                else:
                    formatted_value = f"₹{value:.2f}"
                    
                table_data.append({
                    "Year": date.year,
                    "Age": self.current_age + years_contributed,
                    "Corpus Value": formatted_value,
                    "Monthly Contribution": f"₹{current_monthly_contribution:.2f}"
                })
        
        return table_data    
    
    def export_to_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)
        pdf.cell(200, 10, txt="NPS Pension Projection Summary", ln=True, align='C')

        # Format large numbers for better display - using Rs. instead of ₹ symbol
        def format_amount(val):
            if val >= 1e7:  # Above 1 crore
                return f"Rs.{val/1e7:.2f} Crore ({val:.2f})"
            elif val >= 1e5:  # Above 1 lakh
                return f"Rs.{val/1e5:.2f} Lakh ({val:.2f})"
            else:
                return f"Rs.{val:.2f}"

        items = {
            "Date of Birth": self.birth_date.strftime("%d-%m-%Y"),
            "Current Age": f"{self.current_age} years",
            "Retirement Age": f"{self.retirement_age} years",
            "Retirement Date": self.retirement_date.strftime("%d-%m-%Y"),
            "Total Retirement Corpus": f"{format_amount(self.total_corpus)} ({self.total_corpus_words})",
            "Annuity Corpus": f"{format_amount(self.annuity_corpus)} ({self.annuity_corpus_words})",
            "Lump Sum": f"{format_amount(self.lump_sum)} ({self.lump_sum_words})",
            "Estimated Monthly Pension(Considering Annuity rate of 6%)": f"{format_amount(self.monthly_pension)} ({self.monthly_pension_words})",
            "Total Invested": f"{format_amount(self.total_invested)} ({self.total_invested_words})",
            "Growth": f"{format_amount(self.growth)} ({self.growth_words})"
        }

        pdf.set_font("Arial", size=10)  # Smaller font size for detailed info
        for key, value in items.items():
            pdf.multi_cell(0, 10, txt=f"{key}: {value}", align='L')
        
        # Add developer credit at the bottom of the PDF
        pdf.ln(10)  # Add some space
        pdf.set_font("Arial", 'I', size=8)  # Italic style for credits
        pdf.cell(0, 10, txt="Developed by Saptarshi Sanyal, Asansol, WB, India", ln=True, align='C')

        # Use 'bytes' mode to avoid encoding issues
        try:
            pdf_output = pdf.output(dest='S').encode('latin-1')
        except UnicodeEncodeError:
            # Fallback if any Unicode characters cause issues
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=14)
            pdf.cell(200, 10, txt="NPS Pension Projection Summary", ln=True, align='C')
            
            pdf.set_font("Arial", size=10)
            for key, value in items.items():
                # Remove any potential Unicode characters
                safe_value = value.replace('₹', 'Rs.')
                pdf.multi_cell(0, 10, txt=f"{key}: {safe_value}", align='L')
            
            # Add developer credit at the bottom of the PDF (in fallback mode)
            pdf.ln(10)  # Add some space
            pdf.set_font("Arial", 'I', size=8)  # Italic style for credits
            pdf.cell(0, 10, txt="Developed by Saptarshi Sanyal, Asansol, WB, India", ln=True, align='C')
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            
        return io.BytesIO(pdf_output)

# Apply CSS for faster loading and better appearance
# ... (keep all the existing imports and class definitions the same until the apply_custom_css function)

# Updated CSS with more prominent colors and better styling
# ... (keep all the existing imports and class definitions the same until the apply_custom_css function)

# Updated CSS with white bold headings and values
def apply_custom_css():
    st.markdown("""
    <style>
    /* Faster loading by reducing animations */
    .stButton button {
        transition: none !important;
    }
    
    /* Better appearance for metrics with white bold headings */
    div[data-testid="stMetric"] {
        background-color: rgba(28, 43, 65, 0.8);  /* Darker background for contrast */
        border-radius: 5px;
        padding: 10px 15px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border: 1px solid #2a4a7a;
    }
    
    div[data-testid="stMetric"] > div:first-child {
        margin-bottom: 5px;
    }
    
    div[data-testid="stMetric"] > div:first-child > p {
        font-weight: 700 !important;  /* Bolder font */
        font-size: 1.1rem !important;
        color: white !important;  /* White color for headings */
    }
    
    div[data-testid="stMetric"] label {
        color: white !important;
        font-weight: 600 !important;
    }
    
    /* Make metric values white and bold */
    div[data-testid="stMetric"] > div[data-testid="stMetricValue"] > div {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.3rem !important;
    }
    
    /* Make form inputs more compact and organized */
    div[data-testid="stNumberInput"] {
        margin-bottom: 0.8rem;
    }
    
    /* Make slider labels more prominent */
    .stSlider label {
        font-weight: 500;
    }
    
    /* Optimize loading by disabling parallax effect */
    .main {
        background-image: none !important;
    }
    
    /* Better table appearance */
    div[data-testid="stTable"] {
        max-height: 400px;
        overflow-y: auto;
    }
    
    /* Word descriptions styling - white bold */
    .word-value {
        font-size: 0.95rem !important;
        color: white !important;
        font-weight: 600 !important;
        margin-top: 5px;
        font-style: normal !important;
    }
    
    /* Section headers */
    .section-header {
        color: #0068c9;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Make the main title more prominent */
    h1 {
        color: white !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }
    
    /* Darker background for better contrast */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Better tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0e1117;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# -------- Streamlit Interface --------
def main():
    st.set_page_config(layout="wide", page_title="NPS Calculator", page_icon="📈")
    apply_custom_css()
    
    # Use container for better performance
    with st.container():
        st.markdown(
            """
            <h1 style='text-align: center;'>📈 NPS Pension Calculator</h1>
            """,
            unsafe_allow_html=True
        )

    # Use a single column form instead of tabs for better performance
    with st.form("nps_form"):
        # Personal Information Section
        st.markdown("<div class='section-header'>Personal Information</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            # Simpler date input for better performance
            st.write("Enter Date of Birth")
            date_cols = st.columns(3)
            with date_cols[0]:
                day = st.number_input("Day", min_value=1, max_value=31, value=1, format="%d", key="dob_day")
            with date_cols[1]:
                month = st.number_input("Month", min_value=1, max_value=12, value=1, format="%d", key="dob_month")
            with date_cols[2]:
                year = st.number_input("Year", min_value=1940, max_value=datetime.date.today().year, value=1990, key="dob_year")
            
            try:
                birth_date = datetime.date(year, month, day)
            except ValueError:
                # Handle invalid date more efficiently
                day = min(day, 28 if month == 2 else 30 if month in [4, 6, 9, 11] else 31)
                birth_date = datetime.date(year, month, day)
            
        with col2:
            retirement_age = st.number_input("Retirement Age", min_value=40, max_value=80, value=60)
        
        # Investment Details Section - each input on separate line
        st.markdown("<div class='section-header'>Investment Details</div>", unsafe_allow_html=True)
        current_balance = st.number_input("Current NPS Balance (₹)", min_value=0.0, value=0.0)
        monthly_contribution = st.number_input("Monthly Contribution (₹)", min_value=0.0, value=0.0)
        annual_increase = st.slider("Annual Increase in Contribution (%)", 0, 20, 5)
        
        # Pension Details Section
        st.markdown("<div class='section-header'>Pension Details</div>", unsafe_allow_html=True)
        annuity_ratio = st.slider("Annuity Ratio (%) - You have to sacrifice this amount from you accumulated corpus to get pension benefit", 0, 100, 40, 
                                help="Percentage of corpus to be used for purchasing annuity to get monthly pension")
        
        # Return Rate Section
        st.markdown("<div class='section-header'>Expected Returns</div>", unsafe_allow_html=True)
        annual_return_rate = st.slider("Expected Annual Return (%)", 1, 20, 10)

        submitted = st.form_submit_button("Calculate", type="primary")

    if submitted:
        try:
            # Progress indicator for better UX during computation
            with st.spinner("Calculating your pension details..."):
                nps = NPSCalculator(
                    birth_date=birth_date,
                    current_balance=current_balance,
                    monthly_contribution=monthly_contribution,
                    annuity_ratio=annuity_ratio / 100,  # Convert to decimal
                    annual_return_rate=annual_return_rate / 100,  # Convert to decimal
                    annual_increase_rate=annual_increase / 100,  # Convert to decimal
                    retirement_age=retirement_age
                )

            current_date = datetime.date.today()
            age = relativedelta(current_date, birth_date).years
            
            st.markdown(f"""
            <div style='color: white;'>
            <p><strong>Basic Information:</strong></p>
            <ul style='margin-top: 0; padding-left: 20px;'>
                <li>Current Age: {age} years</li>
                <li>Years to Retirement: {retirement_age - age} years</li>
                <li>Projected Retirement Date: {nps.retirement_date.strftime("%d %b %Y")}</li>
                <li>Months to Retirement: {nps.months}</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

            # Create tabs for organizing results
            tab1, tab2, tab3 = st.tabs(["Summary Results", "Detailed Yearwise Projections", "Formulas used"])
            
            with tab1:
                st.subheader("📊 Results")
                
                # Format function for metrics
                def format_metric_value(value):
                    if value >= 10000000:  # 1 crore
                        return f"₹{value/10000000:.2f} Cr"
                    elif value >= 100000:  # 1 lakh
                        return f"₹{value/100000:.2f} L"
                    else:
                        return f"₹{value:.2f}"
                
                # Create columns for metrics with word values
                results_col1, results_col2 = st.columns(2)
                
                with results_col1:
                    st.metric("Total Corpus at Retirement", format_metric_value(nps.total_corpus))
                    st.markdown(f"<div class='word-value'>{nps.total_corpus_words}</div>", unsafe_allow_html=True)
                    
                    st.metric("Annuity Corpus(This amount will debited from accumulated corpus to get pension benefit)", format_metric_value(nps.annuity_corpus))
                    st.markdown(f"<div class='word-value'>{nps.annuity_corpus_words}</div>", unsafe_allow_html=True)
                    
                    st.metric("Lump Sum Withdrawal", format_metric_value(nps.lump_sum))
                    st.markdown(f"<div class='word-value'>{nps.lump_sum_words}</div>", unsafe_allow_html=True)
                
                with results_col2:
                    st.metric("Estimated Monthly Pension (Considering annuity rate 6%)", format_metric_value(nps.monthly_pension))
                    st.markdown(f"<div class='word-value'>{nps.monthly_pension_words}</div>", unsafe_allow_html=True)
                    
                    st.metric("Total Invested", format_metric_value(nps.total_invested))
                    st.markdown(f"<div class='word-value'>{nps.total_invested_words}</div>", unsafe_allow_html=True)
                    
                    st.metric("Growth", format_metric_value(nps.growth))
                    st.markdown(f"<div class='word-value'>{nps.growth_words}</div>", unsafe_allow_html=True)

                # Bar chart with optimized layout
                st.pyplot(nps.generate_bar_chart(), use_container_width=True)
                
                # Pie chart and line chart side by side with adjusted widths
                chart_col1, chart_col2 = st.columns([1, 1.5])
                
                with chart_col1:
                    st.pyplot(nps.generate_pie_chart())
                
                with chart_col2:
                    st.pyplot(nps.generate_line_chart())
            
            with tab2:
                st.subheader("📅 Yearly Projection Details")
                show_all = st.checkbox("Show all years", value=True, key="show_all_years")
                yearly_data = nps.generate_detailed_table(show_all_years=show_all)
                st.table(yearly_data)
            
            with tab3:
                st.subheader("📚 Formulas Used")
                st.markdown(r"""
                **Monthly Compounding with Increasing Contributions:**  
                $$FV = \sum_{t=1}^{T} P_t \times (1 + r)^{T-t+1}$$  
                where $P_t = P_0 \times (1 + g)^{\lfloor(t-1)/12\rfloor}$

                **Future Value of Current Corpus:**  
                $$FV = B \times (1 + R)^T$$

                **Monthly Pension from Annuity Corpus:**  
                $$P = \frac{A \times a}{12}$$

                **Where:**  
                - $P_0$: Initial Monthly Contribution  
                - $g$: Annual increase in contribution  
                - $r$: Monthly return rate ($R/12$)  
                - $T$: Months to retirement  
                - $B$: Current NPS Balance  
                - $R$: Annual return rate  
                - $A$: Annuity Corpus  
                - $a$: Annuity Rate
                """)

            # Export PDF button
            pdf_file = nps.export_to_pdf()
            st.download_button(
                label="📄 Download Summary as PDF",
                data=pdf_file,
                file_name="nps_summary.pdf",
                mime="application/pdf",
                key="download_pdf"
            )

        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            
    st.markdown("""
    <div style="position: fixed; bottom: 10px; left: 0; right: 0; text-align: center; padding: 10px; 
                background-color: rgba(14, 17, 23, 0.8); border-top: 1px solid #2a4a7a;">
        <p style="color: #a3a8b8; font-size: 0.8rem; margin: 0;">
            Developed by Saptarshi Sanyal, Asansol, WB, India
        </p>
    </div>
    """, unsafe_allow_html=True)    

if __name__ == "__main__":
    main()