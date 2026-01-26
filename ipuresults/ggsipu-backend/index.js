const express = require("express");
const cors = require("cors");
const { chromium } = require("playwright");

const { loadCredits } = require("../analytics/creditLoader");
const { calculateAnalytics } = require("../analytics/cgpaCalculator");

const app = express();
app.use(cors());
app.use(express.json());

let browser, page;

// load credits once
const creditMaps = loadCredits("../analytics/credits.csv");

// ---------- INIT LOGIN (CAPTCHA) ----------
app.get("/init-login", async (req, res) => {
    try {
        browser = await chromium.launch({ headless: true });
        page = await browser.newPage();

        await page.goto("https://examweb.ggsipu.ac.in/web/login.jsp", {
            waitUntil: "networkidle",
        });

        await page.waitForSelector("#captchaImage");
        const captchaElement = await page.$("#captchaImage");
        const captchaBuffer = await captchaElement.screenshot();

        res.json({
            captcha: captchaBuffer.toString("base64"),
        });
    } catch (err) {
        if (browser) await browser.close();
        res.status(500).json({ success: false, message: err.message });
    }
});

// ---------- LOGIN + RESULT + ANALYTICS ----------
app.post("/submit-login", async (req, res) => {
    const { username, password, captcha } = req.body;

    try {
        // login
        await page.fill("#username", username);
        await page.fill("#passwd", password);
        await page.fill("#captcha", captcha);
        await page.click(".btn-login");

        await page.waitForURL("**/studenthome.jsp", { timeout: 15000 });

        // select ALL semesters
        await page.waitForSelector("#euno");
        await page.selectOption("#euno", "100");

        // get result
        await page.click(".btn-submit");
        await page.waitForSelector("table.modern-table");

        // scrape result
        const scraped = await page.evaluate(() => {
            const studentInfo = {};
            document
                .querySelectorAll(".student-info-card .info-item")
                .forEach((i) => {
                    const k = i.querySelector(".info-label")?.innerText.trim();
                    const v = i.querySelector(".info-value")?.innerText.trim();
                    if (k && v) studentInfo[k] = v;
                });

            const subjects = Array.from(
                document.querySelectorAll("table.modern-table tbody tr"),
            ).map((row) => {
                const t = row.querySelectorAll("td");
                return {
                    semester: t[0].innerText.trim(),
                    paperCode: t[1].innerText.trim(),
                    subjectName: t[2].innerText.trim(),
                    internal: t[3].innerText.trim(),
                    external: t[4].innerText.trim(),
                    total: t[5].innerText.trim(),
                    exam: t[6].innerText.trim(),
                    declaredDate: t[7].innerText.trim(),
                };
            });

            return { studentInfo, subjects };
        });

        // ---------- ANALYTICS ----------
        const analytics = calculateAnalytics(scraped.subjects, creditMaps);
        await browser.close();

        res.json({
            success: true,
            message: "Result fetched successfully",
            studentInfo: scraped.studentInfo,
            analytics,
        });
    } catch (err) {
        if (browser) await browser.close();
        res.json({ success: false, message: err.message });
    }
});

app.listen(9999, () => {
    console.log("Backend running on http://127.0.0.1:9999");
});
