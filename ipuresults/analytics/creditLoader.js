const fs = require("fs");

function normalize(text) {
    return text
        .toLowerCase()
        .replace(/&/g, "and")
        .replace(/[^a-z0-9\s]/g, "")
        .replace(/\s+/g, " ")
        .trim();
}

function loadCredits(csvPath) {
    const csv = fs.readFileSync(csvPath, "utf8");
    const lines = csv.split("\n").slice(1);

    const byCode = {};
    const byName = {};

    for (const line of lines) {
        if (!line.trim()) continue;

        const [code, name, credits] = line.split(",");

        const cleanCode = code.trim();
        const cleanName = name.trim();
        const creditVal = Number(credits);

        byCode[cleanCode] = {
            subjectName: cleanName,
            credits: creditVal,
        };

        byName[normalize(cleanName)] = {
            credits: creditVal,
        };
    }

    return { byCode, byName };
}

module.exports = { loadCredits, normalize };
