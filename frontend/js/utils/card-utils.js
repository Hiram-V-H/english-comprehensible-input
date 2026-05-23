export const STRIPE_GRADIENTS = [
    'linear-gradient(90deg, #8b6a4a, #c4a040, #6b4a2a)',
    'linear-gradient(90deg, #6b4a2a, #8b6a4a, #6b4a2a)',
    'linear-gradient(90deg, #5a8a4a, #7ab06a, #5a8a4a)',
    'linear-gradient(90deg, #8b6a9a, #a090b0, #8b6a9a)',
    'linear-gradient(90deg, #b8705a, #c4907a, #b8705a)',
];

export function getDifficultyColors(unknownDensity) {
    if (unknownDensity == null) return {
        barColor: '#a08060',
        barBg: '#a08060',
    };
    if (unknownDensity < 0.05) return {
        barColor: '#5a8a4a',
        barBg: 'linear-gradient(90deg, #5a8a4a, #7ab06a)',
    };
    if (unknownDensity < 0.15) return {
        barColor: '#c4a040',
        barBg: 'linear-gradient(90deg, #c4a040, #d4b860)',
    };
    return {
        barColor: '#b8543a',
        barBg: 'linear-gradient(90deg, #b8543a, #c8705a)',
    };
}

export function getI1ScoreLabel(score) {
    if (score == null) return null;
    if (score >= 0.8) return 'Ideal';
    if (score >= 0.5) return 'Challenging';
    return 'Difficult';
}
