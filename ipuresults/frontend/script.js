const API = "http://127.0.0.1:9999";

// Load captcha immediately when script loads (if on login page)
if (document.readyState === 'loading') {
    // If DOM is still loading, wait for it
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.location.pathname.includes("dashboard")) {
            loadCaptcha();
        }
    });
} else {
    // DOM is already loaded
    if (!window.location.pathname.includes("dashboard")) {
        loadCaptcha();
    }
}

// Helper function to safely format numbers
function formatNumber(value, decimalPlaces = 2) {
    if (typeof value === "number" && !isNaN(value)) {
        return value.toFixed(decimalPlaces);
    }
    return "N/A";
}

// ---------- PASSWORD VISIBILITY TOGGLE ----------
function togglePasswordVisibility() {
    const passwordInput = document.getElementById("password");
    const eyeIcon = document.getElementById("eyeIcon");
    const eyeOffIcon = document.getElementById("eyeOffIcon");
    
    if (!passwordInput || !eyeIcon || !eyeOffIcon) return;
    
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        eyeIcon.style.display = "none";
        eyeOffIcon.style.display = "block";
    } else {
        passwordInput.type = "password";
        eyeIcon.style.display = "block";
        eyeOffIcon.style.display = "none";
    }
}

// ---------- CAPTCHA ----------
async function loadCaptcha() {
    const img = document.getElementById("captchaImg");
    const loader = document.getElementById("captchaLoader");
    if (!img || !loader) return;

    // Show loader, hide image
    loader.style.display = "flex";
    img.style.display = "none";

    try {
        const res = await fetch(API + "/init-login");
        const data = await res.json();

        // Set image source and wait for it to load
        img.onload = () => {
            // Hide loader, show image
            loader.style.display = "none";
            img.style.display = "block";
        };
        
        img.onerror = () => {
            // If image fails to load, show error
            loader.innerHTML = '<span style="color: #dc2626;">Failed to load captcha. Click reload.</span>';
        };

        img.src = "data:image/png;base64," + data.captcha;
    } catch (err) {
        console.error("Captcha fetch failed", err);
        loader.innerHTML = '<span style="color: #dc2626;">Failed to load captcha. Click reload.</span>';
    }
}

// ---------- LOGIN ----------
async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const captcha = document.getElementById("captcha").value;
    const status = document.getElementById("status");

    status.innerText = "Fetching result...";

    const res = await fetch(API + "/submit-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, captcha }),
    });

    const data = await res.json();

    if (!data.success) {
        status.innerText = data.message;
        loadCaptcha();
        return;
    }

    localStorage.setItem("resultData", JSON.stringify(data));
    window.location.href = "dashboard.html";
}

// ---------- DASHBOARD LOGIC ----------
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("dashboard")) {
        const saved = localStorage.getItem("resultData");
        if (saved) {
            const resultData = JSON.parse(saved);
            const transformedData = transformData(resultData);
            window.transformedData = transformedData;
            console.log("Transformed Data:", transformedData); // Log transformedData
            populateDashboard(transformedData);
        }

        // Logout functionality
        const logoutButton = document.getElementById("logoutButton");
        if (logoutButton) {
            logoutButton.addEventListener("click", () => {
                localStorage.removeItem("resultData"); // Clear stored data
                window.location.href = "index.html"; // Redirect to login page
            });
        }

        function populateOverallSummary(overallData) {
            const summaryGrid = document.querySelector(
                "#overall .summary-grid",
            );
            if (summaryGrid) {
                summaryGrid.innerHTML = `
                    <div class="summary-item highlight">
                        <span class="summary-label">CGPA</span>
                        <span class="summary-value">${overallData.cgpa}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Equivalent Percentage</span>
                        <span class="summary-value">${overallData.equivalentPercentage}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Total Marks</span>
                        <span class="summary-value">${overallData.marks}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Percentage</span>
                        <span class="summary-value">${overallData.percentage}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Credit Marks</span>
                        <span class="summary-value">${overallData.creditMarks}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Credit Percentage</span>
                        <span class="summary-value">${overallData.creditPercentage}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Credits Obtained</span>
                        <span class="summary-value">${overallData.creditsObtained}</span>
                    </div>
                `;
            }
        }

        // Replace the populateSemesterDetails function in script.js with this:

        function populateSemesterDetails(semesterNum, semesterData) {
            console.log(
                `Populating Semester ${semesterNum} with data:`,
                semesterData,
            );

            // Populate Semester Summary
            const summaryGrid = document.getElementById(
                `sem${semesterNum}-summary`,
            );
            if (summaryGrid) {
                const sgpa = semesterData.sgpa || 0;
                const totalMarks = semesterData.totalMarks || 0;
                const maxMarks = semesterData.maxMarks || 0;
                const percentage = semesterData.percentage || 0;
                const creditMarks = semesterData.creditMarks || 0;
                const maxCreditMarks = semesterData.maxCreditMarks || 0;
                const creditPercentage = semesterData.creditPercentage || 0;
                const totalCredits = semesterData.totalCredits || 0;

                summaryGrid.innerHTML = `
            <div class="summary-item highlight">
                <span class="summary-label">SGPA</span>
                <span class="summary-value">${formatNumber(sgpa)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Equivalent Percentage</span>
                <span class="summary-value">${formatNumber(sgpa * 10)}%</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Total Marks</span>
                <span class="summary-value">${formatNumber(totalMarks, 0)} / ${formatNumber(maxMarks, 0)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Percentage</span>
                <span class="summary-value">${formatNumber(percentage)}%</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Credit Marks</span>
                <span class="summary-value">${formatNumber(creditMarks, 0)} / ${formatNumber(maxCreditMarks, 0)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Credit Percentage</span>
                <span class="summary-value">${formatNumber(creditPercentage)}%</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Credits Obtained</span>
                <span class="summary-value">${formatNumber(totalCredits, 0)} / ${formatNumber(totalCredits, 0)}</span>
            </div>
        `;
            }

            // Populate Subjects Breakdown Table
            const subjectsTbody = document.getElementById(
                `sem${semesterNum}-subjects`,
            );
            if (subjectsTbody && semesterData.subjects) {
                subjectsTbody.innerHTML = ""; // Clear previous content

                console.log(
                    `Number of subjects for semester ${semesterNum}:`,
                    semesterData.subjects.length,
                );

                if (semesterData.subjects.length === 0) {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                <td colspan="7" style="text-align: center; padding: 2rem; color: var(--gray-500);">
                    No subjects found for this semester
                </td>
            `;
                    subjectsTbody.appendChild(row);
                } else {
                    semesterData.subjects.forEach((subject, index) => {
                        console.log(`Subject ${index}:`, subject);

                        // Extract and display values, with proper fallbacks
                        const paperCode = (subject.paperCode && subject.paperCode.trim() !== '') ? subject.paperCode.trim() : "N/A";
                        const subjectName = (subject.subjectName && subject.subjectName.trim() !== '') ? subject.subjectName.trim() : "N/A";
                        const internal = (subject.internal !== undefined && 
                                         subject.internal !== null && 
                                         subject.internal.toString().trim() !== '') 
                                         ? subject.internal.toString().trim() 
                                         : "0";
                        const external = (subject.external !== undefined && 
                                         subject.external !== null && 
                                         subject.external.toString().trim() !== '') 
                                         ? subject.external.toString().trim() 
                                         : "0";
                        const total = (subject.total !== undefined &&
                                      subject.total !== null &&
                                      subject.total.toString().trim() !== '')
                                      ? subject.total.toString().trim()
                                      : (subject.marks !== undefined && subject.marks !== null)
                                        ? subject.marks.toString()
                                        : "0";
                        const credits = (subject.credits !== undefined &&
                                        subject.credits !== null)
                                        ? subject.credits.toString()
                                        : "0";
                        const grade = (subject.grade && subject.grade.toString().trim() !== '') ? subject.grade.toString().trim() : "N/A";

                        const row = document.createElement("tr");
                        row.innerHTML = `
                    <td>${paperCode}</td>
                    <td>${subjectName}</td>
                    <td>${internal}</td>
                    <td>${external}</td>
                    <td>${total}</td>
                    <td>${credits}</td>
                    <td>${grade}</td>
                `;
                        subjectsTbody.appendChild(row);
                    });
                }
            }
        }
        function populateDashboard(data) {
            const {
                studentInfo,
                overall,
                semesters,
                yearWise,
                cumulativeSemester,
                cumulativeYear,
            } = data;

            // Populate student profile
            populateStudentProfile(studentInfo);

            // Populate overall summary
            populateOverallSummary(overall);

            populateResultBreakdownTable(semesters);
            populateYearWiseTable(yearWise);
            populateCumulativeSemesterTable(cumulativeSemester);
            populateCumulativeYearTable(cumulativeYear);
        }

        function populateStudentProfile(studentInfo) {
            if (!studentInfo || Object.keys(studentInfo).length === 0) {
                return;
            }

            const profileName = document.getElementById("profileName");
            const profileSubtitle = document.getElementById("profileSubtitle");
            const profileDetails = document.getElementById("profileDetails");

            // Extract common fields - only get first match to avoid duplicates
            const nameFields = ['Name', 'Student Name', 'Full Name', 'Student'];
            const enrollmentFields = ['Enrollment Number', 'Enrollment No', 'Enrollment', 'Enroll No'];
            const programFields = ['Program', 'Course', 'Programme', 'Degree'];
            const branchFields = ['Branch', 'Department', 'Stream', 'Specialization'];

            let studentName = '';
            let enrollment = '';
            let program = '';
            let branch = '';

            // Find values for common fields - only first match
            for (const [key, value] of Object.entries(studentInfo)) {
                const keyLower = key.toLowerCase();
                if (!studentName && nameFields.some(f => keyLower.includes(f.toLowerCase()))) {
                    studentName = value;
                } else if (!enrollment && enrollmentFields.some(f => keyLower.includes(f.toLowerCase()))) {
                    enrollment = value;
                } else if (!program && programFields.some(f => keyLower.includes(f.toLowerCase()))) {
                    program = value;
                } else if (!branch && branchFields.some(f => keyLower.includes(f.toLowerCase()))) {
                    branch = value;
                }
            }

            // Set profile name and subtitle
            if (studentName) {
                profileName.textContent = studentName;
            } else {
                profileName.textContent = "Student Profile";
            }

            if (enrollment) {
                profileSubtitle.textContent = enrollment;
            } else if (program) {
                profileSubtitle.textContent = program;
            } else {
                profileSubtitle.textContent = "GGSIPU Student";
            }

            // Create compact details - only show essential unique fields
            // Don't show enrollment in details if it's already in subtitle
            profileDetails.innerHTML = '';
            const displayedValues = new Set();

            // Only show program and branch if they exist and are unique
            // Skip enrollment if it's already shown in subtitle
            if (program && !displayedValues.has(program) && program !== enrollment) {
                displayedValues.add(program);
                const detailItem = createDetailItem('Program', program);
                profileDetails.appendChild(detailItem);
            }
            
            if (branch && !displayedValues.has(branch) && branch !== enrollment) {
                displayedValues.add(branch);
                const detailItem = createDetailItem('Branch', branch);
                profileDetails.appendChild(detailItem);
            }
            
            // Only show enrollment in details if it's NOT in subtitle (i.e., if name was used in subtitle instead)
            if (enrollment && !displayedValues.has(enrollment) && profileSubtitle.textContent !== enrollment) {
                displayedValues.add(enrollment);
                const detailItem = createDetailItem('Enrollment', enrollment);
                profileDetails.appendChild(detailItem);
            }
        }

        function createDetailItem(label, value) {
            const item = document.createElement('div');
            item.className = 'profile-detail-item';
            item.innerHTML = `
                <span class="detail-label">${label}</span>
                <span class="detail-value">${value}</span>
            `;
            return item;
        }

        function populateResultBreakdownTable(
            semesters,
            showCreditMarks = false,
        ) {
            const resultBreakdownTbody = document.querySelector(
                "#resultBreakdownTable tbody",
            );
            resultBreakdownTbody.innerHTML = "";
            for (const sem in semesters) {
                const semester = semesters[sem];
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${sem}</td>
                    <td>${showCreditMarks ? semester.creditMarks + "/" + semester.maxCreditMarks : semester.totalMarks + "/" + semester.maxMarks}</td>
                    <td>${showCreditMarks ? semester.creditPercentage.toFixed(2) : semester.percentage.toFixed(2)}%</td>
                    <td>${semester.sgpa.toFixed(2)}</td>
                `;
                resultBreakdownTbody.appendChild(row);
            }
        }

        function populateYearWiseTable(yearWise, showCreditMarks = false) {
            const yearwiseResultTbody = document.querySelector(
                "#yearwiseResultTable tbody",
            );
            yearwiseResultTbody.innerHTML = "";
            for (const year in yearWise) {
                const yearData = yearWise[year];
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${year}</td>
                    <td>${yearData.totalMarks}/${yearData.maxMarks}</td>
                    <td>${yearData.percentage.toFixed(2)}%</td>
                    <td>${yearData.gpa.toFixed(2)}</td>
                `;
                yearwiseResultTbody.appendChild(row);
            }
        }

        function populateCumulativeSemesterTable(
            cumulativeSemester,
            showCreditMarks = false,
        ) {
            const cumulativeResultTbody1 = document.querySelector(
                "#cumulativeResultTable1 tbody",
            );
            cumulativeResultTbody1.innerHTML = "";
            for (const sem in cumulativeSemester) {
                const semester = cumulativeSemester[sem];
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${sem}</td>
                    <td>${semester.marks}</td>
                    <td>${semester.percentage}</td>
                    <td>${semester.gpa}</td>
                `;
                cumulativeResultTbody1.appendChild(row);
            }
        }

        function populateCumulativeYearTable(
            cumulativeYear,
            showCreditMarks = false,
        ) {
            const cumulativeResultTbody2 = document.querySelector(
                "#cumulativeResultTable2 tbody",
            );
            cumulativeResultTbody2.innerHTML = "";
            for (const year in cumulativeYear) {
                const yearData = cumulativeYear[year];
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${year}</td>
                    <td>${yearData.marks}</td>
                    <td>${yearData.percentage}</td>
                    <td>${yearData.gpa}</td>
                `;
                cumulativeResultTbody2.appendChild(row);
            }
        }

        // Tab switching
        const tabs = document.querySelectorAll(".tabs-nav .tab-btn"); // Corrected selector
        const tabContents = document.querySelectorAll(".tab-content");

        tabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                tabs.forEach((t) => t.classList.remove("active"));
                tab.classList.add("active");

                tabContents.forEach((c) => c.classList.remove("active"));

                const tabId = tab.dataset.tab;
                const tabContent = document.getElementById(tabId);
                if (tabContent) {
                    tabContent.classList.add("active");

                    // If it's a semester tab, populate its details
                    if (tabId.startsWith("sem") && tabId !== "overall") {
                        const semesterNum = parseInt(tabId.replace("sem", ""));
                        if (window.transformedData.semesters[semesterNum]) {
                            populateSemesterDetails(
                                semesterNum,
                                window.transformedData.semesters[semesterNum],
                            );
                        }
                    }
                }
            });
        });

        // Conditional display of semester tabs based on available data
        for (let i = 1; i <= 8; i++) {
            // Assuming max 8 semesters
            const semTabButton = document.querySelector(
                `.tab-btn[data-tab="sem${i}"]`,
            );
            const semTabContent = document.getElementById(`sem${i}`);

            if (semTabButton && semTabContent) {
                // Check if data for this semester exists
                // The 'semesters' object in transformedData has keys like '1', '2', etc.
                if (!window.transformedData.semesters[i]) {
                    semTabButton.style.display = "none"; // Hide the button
                    semTabContent.style.display = "none"; // Hide the content as well
                }
            }
        }

        // Toggle switches
        document
            .getElementById("creditToggle1")
            .addEventListener("change", (e) => {
                populateResultBreakdownTable(
                    window.transformedData.semesters,
                    e.target.checked,
                );
            });
        document
            .getElementById("creditToggle2")
            .addEventListener("change", (e) => {
                populateYearWiseTable(
                    window.transformedData.yearWise,
                    e.target.checked,
                );
            });
        document
            .getElementById("creditToggle3")
            .addEventListener("change", (e) => {
                populateCumulativeSemesterTable(
                    window.transformedData.cumulativeSemester,
                    e.target.checked,
                );
                populateCumulativeYearTable(
                    window.transformedData.cumulativeYear,
                    e.target.checked,
                );
            });
        document
            .getElementById("hiddenRowsToggle")
            .addEventListener("change", (e) => {
                const tables = document.querySelectorAll(".table-container");
                tables.forEach((table) => {
                    const hiddenRows = table.querySelectorAll("tr.hidden");
                    hiddenRows.forEach((row) => {
                        row.style.display = e.target.checked
                            ? "table-row"
                            : "none";
                    });
                });
            });
    }
    // Captcha is already loaded at the top of the script
});
