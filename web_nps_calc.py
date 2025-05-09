# nps_app.py

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from fpdf import FPDF
import io

class NPSCalculator:
    def __init__(self, current_age, current_balance, monthly_contribution, annuity_ratio, annual_return_rate, retirement_age=60, annuity_rate=0.06):
        self.current_age = current_age
        self.current_balance = current_balance
        self.monthly_contribution = monthly_contribution
        self.annuity_ratio = annuity_ratio
        self.annual_return_rate = annual_return_rate
        self.retirement_age = retirement_age
        self.annuity_rate = annuity_rate
        self.compute()

    def compute(self):
        self.years = self.retirement_age - self.current_age
        self.months = self.years * 12
        self.monthly_rate = self.annual_return_rate / 12

        self.fv_contributions = self.monthly_contribution * ((1 + self.monthly_rate)**self.months - 1) / self.monthly_rate
        self.fv_current = self.current_balance * (1 + self.annual_return_rate)**self.years
        self.total_corpus = self.fv_contributions + self.fv_current

        self.annuity_corpus = self.total_corpus * self.annuity_ratio
        self.lump_sum = self.total_corpus * (1 - self.annuity_ratio)
        self.monthly_pension = (self.annuity_corpus * self.annuity_rate) / 12

        self.total_invested = (self.monthly_contribution * self.months) + self.current_balance
        self.growth = self.total_corpus - self.total_invested

    def generate_bar_chart(self):
        fig, ax = plt.subplots(figsize=(8, 5))
        categories = ["Total Invested", "Growth", "Total Corpus", "Monthly Pension"]
        values = [self.total_invested, self.growth, self.total_corpus, self.monthly_pension]
        colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]

        bars = ax.bar(categories, values, color=colors)
        ax.yaxis.set_major_formatter(ScalarFormatter(useMathText=False))
        ax.yaxis.set_major_formatter('{x:,.0f}')
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'Rs.{height:,.0f}', ha='center', va='bottom')
        plt.title("Investment Growth vs Monthly Pension")
        plt.ylabel("Amount (Rs.)")
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        return fig

    def generate_pie_chart(self):
        fig, ax = plt.subplots(figsize=(7, 7))
        sizes = [self.lump_sum, self.annuity_corpus]
        labels = [f"Lump Sum: Rs.{self.lump_sum:,.0f}", f"Annuity: Rs.{self.annuity_corpus:,.0f}\n(Rs.{self.monthly_pension:,.0f}/month)"]
        ax.pie(sizes, labels=labels,
               autopct=lambda p: f'{p:.1f}%\n(Rs.{p/100*sum(sizes):,.0f})',
               colors=["#e377c2", "#8c564b"],
               textprops={'fontsize': 9},
               wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
        plt.title("Corpus Distribution")
        return fig

    def export_to_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="NPS Pension Projection Summary", ln=True, align='C')

        items = {
            "Total Retirement Corpus": self.total_corpus,
            "Annuity Corpus": self.annuity_corpus,
            "Lump Sum": self.lump_sum,
            "Estimated Monthly Pension": self.monthly_pension,
            "Total Invested": self.total_invested,
            "Growth": self.growth
        }

        for key, value in items.items():
            pdf.cell(200, 10, txt=f"{key}: Rs.{value:,.2f}", ln=True)

        # Fix: output to string, then encode to bytes
        pdf_output = pdf.output(dest='S').encode('latin-1')
        return io.BytesIO(pdf_output)


# -------- Streamlit Interface --------

st.title("📈 NPS Pension Calculator")

with st.form("nps_form"):
    current_age = st.slider("Current Age", 25, 60, 35)
    current_balance = st.number_input("Current NPS Balance (Rs.)", min_value=0.0, value=100000.0)
    monthly_contribution = st.number_input("Monthly Contribution (Rs.)", min_value=0.0, value=5000.0)
    annuity_ratio = st.slider("Annuity Ratio (%)- From your total corpus, how much amount you want keep for getting pension", 0, 100, 40) / 100
    annual_return_rate = st.slider("Expected Annual Return (%)", 1, 20, 10) / 100

    submitted = st.form_submit_button("Calculate")

if submitted:
    nps = NPSCalculator(
        current_age=current_age,
        current_balance=current_balance,
        monthly_contribution=monthly_contribution,
        annuity_ratio=annuity_ratio,
        annual_return_rate=annual_return_rate
    )

    st.subheader("📊 Results")
    st.write(f"**Total Corpus at Retirement**: Rs.{nps.total_corpus:,.2f}")
    st.write(f"**Annuity Corpus**: Rs.{nps.annuity_corpus:,.2f}")
    st.write(f"**Lump Sum Withdrawal**: Rs.{nps.lump_sum:,.2f}")
    st.write(f"**Estimated Monthly Pension**: Rs.{nps.monthly_pension:,.2f}")

    st.pyplot(nps.generate_bar_chart())
    st.pyplot(nps.generate_pie_chart())

    # Show formulas used - Fixed LaTeX rendering with proper Streamlit syntax
    st.markdown("### 📘 Formulas Used")
    
    st.markdown(r"""
    **Future Value of Contributions**  
    $$FV = P \times \frac{(1 + r)^n - 1}{r}$$
    
    **Future Value of Current Balance**  
    $$FV = B \times (1 + R)^t$$
    
    **Monthly Pension**  
    $$M = \frac{A \times r}{12}$$
    
    **Where:**  
    - $P$: Monthly contribution  
    - $r$: Monthly return rate  
    - $n$: Number of months till retirement  
    - $B$: Current balance  
    - $R$: Annual return rate  
    - $t$: Years till retirement  
    - $A$: Annuity corpus  
    """)

    # PDF download
    pdf_file = nps.export_to_pdf()
    st.download_button(
        label="📄 Download Summary as PDF",
        data=pdf_file,
        file_name="nps_summary.pdf",
        mime="application/pdf"
    )