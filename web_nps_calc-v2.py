# NPS Calculator with Fixed Graph Layout

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from fpdf import FPDF
import io
import datetime
from dateutil.relativedelta import relativedelta

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
        self.yearly_data = []
        self.monthly_data = []
        self.compute()

    def calculate_exact_age(self):
        return relativedelta(self.current_date, self.birth_date).years

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

        fv_contributions = 0
        monthly = self.monthly_contribution
        corpus = self.current_balance
        current_date = self.current_date
        
        # Calculate monthly data for more accurate projections
        for month in range(1, months_to_retirement + 1):
            corpus *= (1 + self.monthly_rate)
            corpus += monthly
            current_date += relativedelta(months=1)
            
            # Record monthly data
            self.monthly_data.append((current_date, corpus))
            
            # Record yearly data (at end of each year)
            if month % 12 == 0 or month == months_to_retirement:
                self.yearly_data.append((current_date, corpus))
            
            # Increase contribution annually (on the anniversary)
            if month % 12 == 0:
                monthly *= (1 + self.annual_increase_rate)

        self.total_corpus = corpus
        self.retirement_date = retirement_date

        self.annuity_corpus = self.total_corpus * self.annuity_ratio
        self.lump_sum = self.total_corpus * (1 - self.annuity_ratio)
        self.monthly_pension = (self.annuity_corpus * self.annuity_rate) / 12

        self.total_invested = 0
        monthly = self.monthly_contribution
        for year in range(int(self.years)):
            self.total_invested += monthly * 12
            monthly *= (1 + self.annual_increase_rate)
        
        # Add partial year investments if retirement doesn't fall on year boundary
        if months_to_retirement % 12 != 0:
            self.total_invested += monthly * (months_to_retirement % 12)
        
        self.total_invested += self.current_balance
        self.growth = self.total_corpus - self.total_invested

    def generate_bar_chart(self):
        fig, ax = plt.subplots(figsize=(6, 2.5))  # Further reduced height
        categories = ["Total Invested", "Growth", "Total Corpus", "Monthly Pension"]
        values = [self.total_invested, self.growth, self.total_corpus, self.monthly_pension]
        colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]

        bars = ax.bar(categories, values, color=colors, width=0.6)  # Reduced bar width for better proportions
        ax.yaxis.set_major_formatter('{x:.0f}')
        
        # Smaller font sizes
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, 
                   f'Rs.{height:.0f}', 
                   ha='center', va='bottom', 
                   fontsize=6)  # Reduced font size further
        
        plt.title("Investment Growth vs Monthly Pension", fontsize=9)  # Smaller title
        plt.ylabel("Amount (Rs.)", fontsize=7)  # Smaller label
        ax.tick_params(axis='x', labelsize=6, rotation=15)  # Smaller, slightly rotated labels
        ax.tick_params(axis='y', labelsize=6)  # Smaller ticks
        plt.grid(axis='y', linestyle='--', alpha=0.5)  # Lighter grid
        plt.tight_layout(pad=0.8)  # Tighter padding
        return fig
    
    def generate_pie_chart(self):
        fig, ax = plt.subplots(figsize=(4, 3))  # Further reduced size to match line chart height
        sizes = [self.lump_sum, self.annuity_corpus]
        labels = [f"Lump Sum: Rs.{self.lump_sum:.0f}", f"Annuity: Rs.{self.annuity_corpus:.0f}"]
        ax.pie(sizes, labels=None,  # Removed labels from pie directly
               autopct=lambda p: f'{p:.1f}%',
               colors=["#e377c2", "#8c564b"],
               wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
        plt.title("Corpus Distribution", fontsize=10)
        
        # Add legend instead of labels for better layout
        ax.legend(labels, loc="center left", bbox_to_anchor=(0.9, 0.5), fontsize=7)
        
        # Add monthly pension as text annotation
        ax.annotate(f"Monthly Pension: Rs.{self.monthly_pension:.0f}", 
                   xy=(0.5, -0.1), xycoords='axes fraction',
                   ha='center', va='center', fontsize=7)
        
        plt.tight_layout()
        return fig

    def generate_line_chart(self):
        dates, values = zip(*self.yearly_data)
        fig, ax = plt.subplots(figsize=(6, 3))  # Adjusted width to better match pie chart
        
        ax.plot(dates, values, marker='o', markersize=3,  # Even smaller markers
                linestyle='-', linewidth=1,  # Thinner line
                color='#1f77b4', label='Yearly Corpus')
        
        # Monthly data with thinner line
        m_dates, m_values = zip(*self.monthly_data)
        ax.plot(m_dates, m_values, linestyle='-', linewidth=0.5, 
                color='#1f77b4', alpha=0.3, label='Monthly Growth')
        
        ax.set_title("NPS Corpus Growth Over Time", fontsize=10)
        ax.set_xlabel("Year", fontsize=8)
        ax.set_ylabel("Corpus Value (Rs.)", fontsize=8)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Move legend to better position to save space
        ax.legend(fontsize=7, loc='upper left')
        
        # Format y-axis
        ax.yaxis.set_major_formatter('Rs.{x:.0f}')
        
        # Reduce number of x-tick labels to avoid crowding
        plt.xticks(rotation=45, fontsize=7)
        plt.yticks(fontsize=7)
        plt.tight_layout(pad=1.0)
        return fig
    
    def generate_detailed_table(self):
        table_data = []
        for date, value in self.yearly_data:
            years_contributed = date.year - self.current_date.year
            current_monthly_contribution = self.monthly_contribution * (1 + self.annual_increase_rate) ** years_contributed
            table_data.append({
                "Year": date.year,
                "Age": self.birth_date.year + (date.year - self.birth_date.year),
                "Corpus Value (Rs.)": f"{value:.2f}",
                "Monthly Contribution (Rs.)": f"{current_monthly_contribution:.2f}"
            })
        return table_data

    def export_to_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)
        pdf.cell(200, 10, txt="NPS Pension Projection Summary", ln=True, align='C')

        items = {
            "Date of Birth": self.birth_date.strftime("%d-%m-%Y"),
            "Current Age": f"{self.current_age} years",
            "Retirement Age": f"{self.retirement_age} years",
            "Retirement Date": self.retirement_date.strftime("%d-%m-%Y"),
            "Total Retirement Corpus": f"Rs.{self.total_corpus:.2f}",
            "Annuity Corpus(You have to sacrifice this amount in order to get pension )": f"Rs.{self.annuity_corpus:.2f}",
            "Lump Sum": f"Rs.{self.lump_sum:.2f}",
            "Estimated Monthly Pension": f"Rs.{self.monthly_pension:.2f}",
            "Total Invested": f"Rs.{self.total_invested:.2f}",
            "Growth": f"Rs.{self.growth:.2f}"
        }

        for key, value in items.items():
            pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

        pdf_output = pdf.output(dest='S').encode('latin-1')
        return io.BytesIO(pdf_output)

# -------- Streamlit Interface --------

st.set_page_config(layout="wide")
st.markdown(
    """
    <h1 style='text-align: center;'>📈 NPS Pension Calculator</h1>
    """,
    unsafe_allow_html=True
)

with st.form("nps_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        # Add custom date formatting using HTML and JavaScript
        st.markdown("""
        <style>
        /* Change the format of the date input */
        div[data-testid="stDateInput"] input {
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Manual input fields for date in DD-MM-YYYY format
        st.write("Enter Date of Birth (DD-MM-YYYY)")
        date_cols = st.columns(3)
        with date_cols[0]:
            day = st.number_input("Day", min_value=1, max_value=31, value=1, format="%02d")
        with date_cols[1]:
            month = st.number_input("Month", min_value=1, max_value=12, value=1, format="%02d")
        with date_cols[2]:
            year = st.number_input("Year", min_value=1940, max_value=datetime.date.today().year, value=1990)
        
        # Convert to date object
        try:
            birth_date = datetime.date(year, month, day)
        except ValueError:
            # Handle invalid date (e.g., February 30)
            st.warning("Invalid date. Using first day of the month.")
            if month == 2:
                day = min(day, 28)  # Simplified handling, not accounting for leap years
            elif month in [4, 6, 9, 11]:
                day = min(day, 30)
            birth_date = datetime.date(year, month, day)
        
    with col2:
        retirement_age = st.number_input("Retirement Age", min_value=40, max_value=80, value=60)
    
    current_balance = st.number_input("Current NPS Balance (Rs.)", min_value=0.0, value=0.0)
    monthly_contribution = st.number_input("Monthly Contribution (Rs.)", min_value=0.0, value=0.0)
    annual_increase = st.slider("% Annual Increase in Contribution", 0, 20, 5) / 100
    annuity_ratio = st.slider("Annuity Ratio (%) - (How much amount you want to sacrifice from your accumulated corpus in order to get monthly pension)", 0, 100, 40) / 100
    annual_return_rate = st.slider("Expected Annual Return (%)", 1, 20, 10) / 100

    submitted = st.form_submit_button("Calculate")

if submitted:
    try:
        nps = NPSCalculator(
            birth_date=birth_date,
            current_balance=current_balance,
            monthly_contribution=monthly_contribution,
            annuity_ratio=annuity_ratio,
            annual_return_rate=annual_return_rate,
            annual_increase_rate=annual_increase,
            retirement_age=retirement_age
        )

        current_date = datetime.date.today()
        age = relativedelta(current_date, birth_date).years
        
        st.markdown(f"""
        **Calculated Values:**
        - Current Age: {age} years
        - Years to Retirement: {retirement_age - age} years
        - Projected Retirement Date: {nps.retirement_date.strftime("%d %b %Y")}
        - Months to Retirement: {nps.months}
        """)

        st.subheader("\U0001F4CA Results")
        
        results_col1, results_col2 = st.columns(2)
        
        with results_col1:
            st.metric("Total Corpus at Retirement", f"Rs.{nps.total_corpus:.2f}")
            st.metric("Annuity Corpus (You have to sacrifice this amount in order to get pension )", f"Rs.{nps.annuity_corpus:.2f}")
            st.metric("Lump Sum Withdrawal", f"Rs.{nps.lump_sum:.2f}")
        
        with results_col2:
            st.metric("Estimated Monthly Pension", f"Rs.{nps.monthly_pension:.2f}")
            st.metric("Total Invested", f"Rs.{nps.total_invested:.2f}")
            st.metric("Growth", f"Rs.{nps.growth:.2f}")

        # Bar chart at the top with constrained width
        col1, col2 = st.columns([2, 1])
        with col1:
            st.pyplot(nps.generate_bar_chart(), use_container_width=True)
        with col2:
            # Empty column to control bar chart width
            pass
        
        # Improved layout for charts - pie chart and line chart side by side
        st.subheader("Portfolio Analysis")
        
        # Create columns with adjusted widths for better proportion between charts
        chart_col1, chart_col2 = st.columns([1, 1.5])
        
        with chart_col1:
            st.pyplot(nps.generate_pie_chart())
        
        with chart_col2:
            st.pyplot(nps.generate_line_chart())
        
        st.subheader("\U0001F4C0 Yearly Projection Details")
        st.table(nps.generate_detailed_table())

        st.markdown("### \U0001F4D8 Formulas Used")
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

        pdf_file = nps.export_to_pdf()
        st.download_button(
            label="\U0001F4C4 Download Summary as PDF",
            data=pdf_file,
            file_name="nps_summary.pdf",
            mime="application/pdf",
            key="download_pdf"
        )

    except ValueError as e:
        st.error(str(e))