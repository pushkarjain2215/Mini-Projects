function getGradePoint(marks) {
    const m = Number(marks);

    if (m >= 90) return 10;
    if (m >= 75) return 9;
    if (m >= 65) return 8;
    if (m >= 55) return 7;
    if (m >= 50) return 6;
    if (m >= 45) return 5;
    if (m >= 40) return 4;
    return 0;
}

module.exports = { getGradePoint };
