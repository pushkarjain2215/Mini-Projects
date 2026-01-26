const express = require("express");
const cors = require("cors");
const { chromium } = require("playwright");

const app = express();
app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
    res.send("Backend is running");
});

let browser;
let page;

app.get("/init-login", async (req, res) => {
    try {
        browser = await chromium.launch({ headless: true });

        page = await browser.newPage({
            userAgent:
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        });

        // cache disable
        await page.route("**/*", (route) => {
            route.continue({
                headers: {
                    ...route.request().headers(),
                    "Cache-Control": "no-cache",
                },
            });
        });

        await page.goto("https://examweb.ggsipu.ac.in/web/login.jsp", {
            waitUntil: "networkidle",
        });

        // captcha fully load hone ka wait
        await page.waitForSelector("#captchaImage");

        await page.waitForFunction(() => {
            const img = document.querySelector("#captchaImage");
            return img && img.complete && img.naturalWidth > 0;
        });

        const captchaElement = await page.$("#captchaImage");
        const captchaBuffer = await captchaElement.screenshot();

        res.json({
            captcha: captchaBuffer.toString("base64"),
        });
    } catch (err) {
        if (browser) await browser.close();
        res.status(500).json({
            success: false,
            message: err.message,
        });
    }
});

app.post("/submit-login", async (req, res) => {
    const { username, password, captcha } = req.body;

    try {
        // ---------- LOGIN ----------
        await page.fill("#username", username);
        await page.fill("#passwd", password);
        await page.fill("#captcha", captcha);

        await page.waitForSelector(".btn-login");
        await page.click(".btn-login");

        // wait for dashboard
        await page.waitForURL("**/studenthome.jsp", { timeout: 15000 });

        // ---------- SELECT SEMESTER (ALL = 100) ----------
        await page.waitForSelector("#euno");
        await page.selectOption("#euno", "100");

        // ---------- CLICK GET RESULT ----------
        await page.waitForSelector(".btn-submit");
        await page.click(".btn-submit");

        // ---------- WAIT FOR RESULT TABLE ----------
        await page.waitForSelector("table.modern-table", { timeout: 15000 });

        // ---------- SCRAPE DATA ----------
        const result = await page.evaluate(() => {
            // student info
            const studentInfo = {};
            document
                .querySelectorAll(".student-info-card .info-item")
                .forEach((item) => {
                    const label = item
                        .querySelector(".info-label")
                        ?.innerText.trim();
                    const value = item
                        .querySelector(".info-value")
                        ?.innerText.trim();
                    if (label && value) studentInfo[label] = value;
                });

            // result table
            const rows = Array.from(
                document.querySelectorAll("table.modern-table tbody tr"),
            );

            const subjects = rows.map((row) => {
                const cells = row.querySelectorAll("td");
                return {
                    semester: cells[0]?.innerText.trim(),
                    paperCode: cells[1]?.innerText.trim(),
                    subjectName: cells[2]?.innerText.trim(),
                    internal: cells[3]?.innerText.trim(),
                    external: cells[4]?.innerText.trim(),
                    total: cells[5]?.innerText.trim(),
                    exam: cells[6]?.innerText.trim(),
                    declaredDate: cells[7]?.innerText.trim(),
                };
            });

            return { studentInfo, subjects };
        });

        await browser.close();

        res.json({
            success: true,
            message: "Result fetched successfully",
            data: result,
        });
    } catch (err) {
        if (browser) await browser.close();
        res.json({
            success: false,
            message: err.message,
        });
    }
});

app.listen(9999, () => {
    console.log("Server running on port 9999");
});
