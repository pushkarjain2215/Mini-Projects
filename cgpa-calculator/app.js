const semSelect = document.getElementById("semSelect");
const branchSelect = document.getElementById("branchSelect");
const subjectEl = document.getElementById("subject");
const progressEl = document.getElementById("progress");
const marksInput = document.getElementById("marks");
const nextBtn = document.getElementById("nextBtn");
const circle = document.getElementById("circle");
const modal = document.getElementById("modal");
const finalSGPA = document.getElementById("finalSGPA");

const shareBtn = document.getElementById("shareBtn");
const shareCard = document.getElementById("shareCard");
const shareSubjects = document.getElementById("shareSubjects");
const shareSGPA = document.getElementById("shareSGPA");
const shareMeta = document.getElementById("shareMeta");

let subjects = [];
let index = 0;
let totalPoints = 0;
let totalCredits = 0;
let marksStore = [];

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

/* SEM */
semSelect.addEventListener("change", () => {
    branchSelect.innerHTML = `<option value="">Select Branch</option>`;
    if (!semSelect.value) return;

    Object.keys(SYLLABUS[semSelect.value]).forEach((branch) => {
        const opt = document.createElement("option");
        opt.value = branch;
        opt.innerText = branch;
        branchSelect.appendChild(opt);
    });

    branchSelect.disabled = false;
});

/* BRANCH */
branchSelect.addEventListener("change", () => {
    subjects = SYLLABUS[semSelect.value][branchSelect.value];

    index = 0;
    totalPoints = 0;
    totalCredits = 0;
    marksStore = [];

    subjectEl.innerText = subjects[0].name;
    progressEl.innerText = `Subject 1 of ${subjects.length}`;

    marksInput.disabled = false;
    nextBtn.disabled = false;
    marksInput.value = "";
    marksInput.focus();

    circle.style.background = `conic-gradient(#6366f1 0deg, #1e293b 0deg)`;
});

/* ENTER KEY */
marksInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        nextSubject();
    }
});

nextBtn.addEventListener("click", nextSubject);

/* CORE */
function nextSubject() {
    const marks = parseInt(marksInput.value, 10);
    if (isNaN(marks) || marks < 0 || marks > 100) return;

    marksStore.push(marks);
    totalPoints += gradePoint(marks) * subjects[index].credits;
    totalCredits += subjects[index].credits;

    index++;

    if (index === subjects.length) {
        finalSGPA.innerText = (totalPoints / totalCredits).toFixed(3);
        modal.style.display = "flex";
        return;
    }

    subjectEl.innerText = subjects[index].name;
    progressEl.innerText = `Subject ${index + 1} of ${subjects.length}`;

    const angle = (index / subjects.length) * 360;
    circle.style.background = `conic-gradient(#6366f1 ${angle}deg, #1e293b ${angle}deg)`;

    marksInput.value = "";
    marksInput.focus();
}

/* SHARE */
shareBtn.addEventListener("click", saveResult);

function saveResult() {
    shareSubjects.innerHTML = "";

    subjects.forEach((s, i) => {
        const row = document.createElement("div");
        row.innerHTML = `<span>${s.name}</span><strong>${marksStore[i]}</strong>`;
        shareSubjects.appendChild(row);
    });

    shareMeta.innerText = `${semSelect.value} • ${branchSelect.value}`;
    shareSGPA.innerText = `SGPA ${finalSGPA.innerText}`;

    html2canvas(shareCard, { scale: 2 }).then((canvas) => {
        const link = document.createElement("a");
        link.download = "SGPA_Result.jpg";
        link.href = canvas.toDataURL("image/jpeg", 0.95);
        link.click();
    });
}``