const semSelect = document.getElementById("semSelect");
const branchSelect = document.getElementById("branchSelect");

const subjectEl = document.getElementById("subject");
const progressEl = document.getElementById("progress");
const marksInput = document.getElementById("marks");
const nextBtn = document.getElementById("nextBtn");
const circle = document.getElementById("circle");

const reviewModal = document.getElementById("reviewModal");
const reviewList = document.getElementById("reviewList");
const confirmBtn = document.getElementById("confirmBtn");

const resultModal = document.getElementById("resultModal");
const finalSGPA = document.getElementById("finalSGPA");

const shareBtn = document.getElementById("shareBtn");
const shareCard = document.getElementById("shareCard");
const shareSubjects = document.getElementById("shareSubjects");
const shareSGPA = document.getElementById("shareSGPA");
const shareMeta = document.getElementById("shareMeta");

let subjects = [];
let marksStore = [];
let index = 0;
let editIndex = null;

/* ---------- GRADE POINT ---------- */
function gradePoint(m) {
    if (m >= 90) return 10;
    if (m >= 75) return 9;
    if (m >= 65) return 8;
    if (m >= 55) return 7;
    if (m >= 50) return 6;
    if (m >= 45) return 5;
    if (m >= 40) return 4;
    return 0;
}

/* ---------- SEM SELECT ---------- */
semSelect.addEventListener("change", () => {
    branchSelect.innerHTML = `<option value="">Select Branch</option>`;
    branchSelect.disabled = true;

    if (!semSelect.value) return;

    Object.keys(SYLLABUS[semSelect.value]).forEach((branch) => {
        const opt = document.createElement("option");
        opt.value = branch;
        opt.innerText = branch;
        branchSelect.appendChild(opt);
    });

    branchSelect.disabled = false;
});

/* ---------- BRANCH SELECT ---------- */
branchSelect.addEventListener("change", () => {
    if (!branchSelect.value) return;

    subjects = SYLLABUS[semSelect.value][branchSelect.value];
    marksStore = [];
    index = 0;
    editIndex = null;

    subjectEl.innerText = subjects[0].name;
    progressEl.innerText = `Subject 1 of ${subjects.length}`;

    marksInput.disabled = false;
    nextBtn.disabled = false;

    marksInput.value = "";
    marksInput.focus();

    updateCircle();
});

/* ---------- INPUT ---------- */
nextBtn.addEventListener("click", submitMarks);
marksInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitMarks();
});

marksInput.addEventListener("focus", () => {
    marksInput.scrollIntoView({ block: "center" });
});

/* ---------- SUBMIT MARKS ---------- */
function submitMarks() {
    const marks = parseInt(marksInput.value, 10);
    if (isNaN(marks) || marks < 0 || marks > 100) return;

    if (editIndex !== null) {
        marksStore[editIndex] = marks;
        editIndex = null;
        marksInput.value = "";
        openReview();
        return;
    }

    marksStore.push(marks);
    index++;

    if (index === subjects.length) {
        marksInput.value = "";
        openReview();
        return;
    }

    subjectEl.innerText = subjects[index].name;
    progressEl.innerText = `Subject ${index + 1} of ${subjects.length}`;

    marksInput.value = "";
    updateCircle();

    marksInput.focus({ preventScroll: true });
}

/* ---------- REVIEW ---------- */
function openReview() {
    reviewList.innerHTML = "";

    subjects.forEach((s, i) => {
        const row = document.createElement("div");
        row.className = "review-row";

        row.innerHTML = `
      <div class="review-info">
        <span>${s.name}</span>
        <small>Marks: ${marksStore[i]}</small>
      </div>
      <button class="review-edit">Edit</button>
    `;

        row.querySelector(".review-edit").onclick = () => {
            reviewModal.style.display = "none";

            editIndex = i;
            subjectEl.innerText = subjects[i].name;
            progressEl.innerText = `Editing Subject ${i + 1}`;

            marksInput.value = marksStore[i];
            marksInput.focus();
        };

        reviewList.appendChild(row);
    });

    reviewModal.style.display = "flex";
}

/* ---------- CONFIRM ---------- */
confirmBtn.addEventListener("click", () => {
    reviewModal.style.display = "none";
    calculateSGPA();
});

/* ---------- CALCULATE ---------- */
function calculateSGPA() {
    let totalPoints = 0;
    let totalCredits = 0;

    subjects.forEach((s, i) => {
        totalPoints += gradePoint(marksStore[i]) * s.credits;
        totalCredits += s.credits;
    });

    finalSGPA.innerText = (totalPoints / totalCredits).toFixed(3);
    resultModal.style.display = "flex";
}

/* ---------- SHARE ---------- */
shareBtn.addEventListener("click", () => {
    shareSubjects.innerHTML = "";

    subjects.forEach((s, i) => {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.justifyContent = "space-between";
        row.style.margin = "6px 0";
        row.innerHTML = `<span>${s.name}</span><strong>${marksStore[i]}</strong>`;
        shareSubjects.appendChild(row);
    });

    shareMeta.innerText = `${semSelect.value} • ${branchSelect.value}`;
    shareSGPA.innerText = `SGPA ${finalSGPA.innerText}`;

    
    html2canvas(shareCard, { scale: 2, backgroundColor: "black" }).then(
        (canvas) => {
            const link = document.createElement("a");
            link.download = "SGPA_Result.jpg";
            link.href = canvas.toDataURL("image/jpeg", 0.95);
            link.click();
        },
    );
});

/* ---------- PROGRESS CIRCLE ---------- */
function updateCircle() {
    const angle = (index / subjects.length) * 360;
    circle.style.background = `conic-gradient(#6366f1 ${angle}deg, #1e293b ${angle}deg)`;
}
