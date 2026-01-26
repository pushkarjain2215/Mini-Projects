const fs = require("fs")
const path = require("path")

function loadCredits(csvPath) {
  const csv = fs.readFileSync(csvPath, "utf8")
  const lines = csv.split("\n").slice(1)

  const creditMap = {}

  for (const line of lines) {
    if (!line.trim()) continue
    const [code, name, credits] = line.split(",")

    creditMap[code.trim()] = {
      subjectName: name.trim(),
      credits: Number(credits)
    }
  }

  return creditMap
}

module.exports = { loadCredits }
