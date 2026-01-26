const { getGradePoint, getGrade } = require("./gradeUtils");
const { normalize } = require("./creditLoader");

function calculateAnalytics(scrapedSubjects, creditMaps) {
    const { byCode, byName } = creditMaps;

    const semesterWise = {};
    let totalCredits = 0;
    let totalCreditPoints = 0;

    for (const sub of scrapedSubjects) {
        const sem = sub.semester;
        const marks = Number(sub.total);
        const gradePoint = getGradePoint(marks);

        let creditEntry = byCode[sub.paperCode];

        // fallback by exact normalized subject name
        if (!creditEntry) {
            creditEntry = byName[normalize(sub.subjectName)];
        }

        if (!creditEntry) {
            console.warn("CREDIT NOT FOUND:", sub.paperCode, sub.subjectName);
            continue;
        }

        const credits = creditEntry.credits;
        const creditPoints = credits * gradePoint;

        if (!semesterWise[sem]) {
            semesterWise[sem] = {
                totalCredits: 0,
                totalCreditPoints: 0,
                subjects: [],
            };
        }

        semesterWise[sem].subjects.push({
            paperCode: sub.paperCode,
            code: sub.paperCode, // Keep for backward compatibility
            subjectName: sub.subjectName,
            internal: sub.internal || "0",
            external: sub.external || "0",
            total: sub.total || marks.toString(),
            marks,
            credits,
            gradePoint,
            creditPoints,
            grade: getGrade(marks),
            exam: sub.exam || "",
            declaredDate: sub.declaredDate || "",
        });

        semesterWise[sem].totalCredits += credits;
        semesterWise[sem].totalCreditPoints += creditPoints;
        totalCredits += credits;
        totalCreditPoints += creditPoints;
    }

    for (const sem in semesterWise) {
        const s = semesterWise[sem];
        s.sgpa = Number((s.totalCreditPoints / s.totalCredits).toFixed(2));
    }

    const cgpa = Number((totalCreditPoints / totalCredits).toFixed(2));

    return { semesterWise, cgpa };
}

module.exports = { calculateAnalytics };
