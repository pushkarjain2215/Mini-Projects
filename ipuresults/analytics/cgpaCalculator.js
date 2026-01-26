const { getGradePoint } = require("./gradeUtils");

function calculateAnalytics(scrapedSubjects, creditMap) {
    const semesterWise = {};
    let totalCreditPoints = 0;
    let totalCredits = 0;

    for (const sub of scrapedSubjects) {
        const sem = sub.semester;
        const code = sub.paperCode;
        const marks = Number(sub.total);

        if (!creditMap[code]) continue;

        const credits = creditMap[code].credits;
        const gradePoint = getGradePoint(marks);
        const creditPoints = credits * gradePoint;

        if (!semesterWise[sem]) {
            semesterWise[sem] = {
                totalCredits: 0,
                totalCreditPoints: 0,
                subjects: [],
            };
        }

        semesterWise[sem].subjects.push({
            code,
            subjectName: sub.subjectName,
            marks,
            credits,
            gradePoint,
            creditPoints,
        });

        semesterWise[sem].totalCredits += credits;
        semesterWise[sem].totalCreditPoints += creditPoints;

        totalCredits += credits;
        totalCreditPoints += creditPoints;
    }

    // Calculate SGPA
    for (const sem in semesterWise) {
        const s = semesterWise[sem];
        s.sgpa = Number((s.totalCreditPoints / s.totalCredits).toFixed(2));
    }

    const cgpa = Number((totalCreditPoints / totalCredits).toFixed(2));

    return { semesterWise, cgpa };
}

module.exports = { calculateAnalytics };
