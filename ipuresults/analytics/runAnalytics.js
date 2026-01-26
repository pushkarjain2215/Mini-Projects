const path = require("path");
const { loadCredits } = require("./creditLoader");
const { calculateAnalytics } = require("./cgpaCalculator");

// 👇 example scraped data (replace with real output)
const scrapedSubjects = [
    {
        semester: "1",
        paperCode: "ES101",
        subjectName: "PROGRAMMING IN C",
        total: "95",
    },
    {
        semester: "1",
        paperCode: "BS105",
        subjectName: "APPLIED PHYSICS I",
        total: "71",
    },
];

// load CSV
const creditMap = loadCredits(path.join(__dirname, "credits.csv"));

// calculate analytics
const analytics = calculateAnalytics(scrapedSubjects, creditMap);

console.log(JSON.stringify(analytics, null, 2));
