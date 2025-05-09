function npsPensionCalculator({
    currentBalance,
    currentAge,
    monthlyContribution,
    retirementAge = 60,
    annualReturnRate = 0.08,
    annuityRatio = 0.4,
    annuityRate = 0.06
}) {
    const yearsLeft = retirementAge - currentAge;
    const monthsLeft = yearsLeft * 12;
    const monthlyRate = annualReturnRate / 12;

    // Future value of monthly contributions
    const fvContributions = monthlyContribution * ((Math.pow(1 + monthlyRate, monthsLeft) - 1) / monthlyRate);

    // Future value of current corpus
    const fvCurrent = currentBalance * Math.pow(1 + annualReturnRate, yearsLeft);

    // Total retirement corpus
    const totalCorpus = fvContributions + fvCurrent;

    // Annuity and lump sum split
    const annuityCorpus = totalCorpus * annuityRatio;
    const lumpSum = totalCorpus * (1 - annuityRatio);

    // Monthly pension
    const monthlyPension = (annuityCorpus * annuityRate) / 12;

    return {
        totalCorpus: totalCorpus.toFixed(2),
        annuityCorpus: annuityCorpus.toFixed(2),
        lumpSum: lumpSum.toFixed(2),
        monthlyPension: monthlyPension.toFixed(2)
    };
}

// Example usage:
const result = npsPensionCalculator({
    currentBalance: 600000,
    currentAge: 45,
    monthlyContribution: 10000
});

console.log(result);
