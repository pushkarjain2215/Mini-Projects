const subjects = [
    { name: "Computational Methods", credits: 4 },
    { name: "Indian Knowledge System", credits: 2 },
    { name: "Discrete Mathematics", credits: 4 },
    { name: "Digital Logic & Computer Design", credits: 4 },
    { name: "Data Structures", credits: 4 },
    { name: "OOP using C++", credits: 4 },
    { name: "Computational Methods Lab", credits: 1 },
    { name: "DLCD Lab", credits: 1 },
    { name: "Data Structures Lab", credits: 1 },
    { name: "OOP Lab", credits: 1 },
];

let index = 0;
let totalPoints = 0;
let totalCredits = 0;

const subjectEl = document.getElementById("subject");
const progressEl = document.getElementById("progress");
const marksInput = document.getElementById("marks");
const circle = document.getElementById("circle");
const modal = document.getElementById("modal");
const finalSGPA = document.getElementById("finalSGPA");
const nextBtn = document.getElementById("nextBtn");

function gradePoint(marks) {
    if (marks >= 90) return 10;
    if (marks >= 75) return 9;
    if (marks >= 65) return 8;
    if (marks >= 55) return 7;
    if (marks >= 50) return 6;
    if (marks >= 45) return 5;
    if (marks >= 40) return 4;
    return 0;
}

nextBtn.addEventListener("click", nextSubject);

marksInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") nextSubject();
});

function nextSubject() {
    if (marksInput.value === "") return;

    const marks = parseInt(marksInput.value);
    const credits = subjects[index].credits;
    const gp = gradePoint(marks);

    totalPoints += gp * credits;
    totalCredits += credits;

    index++;

    if (index === subjects.length) {
        const sgpa = (totalPoints / totalCredits).toFixed(3);
        finalSGPA.innerText = sgpa;
        modal.style.display = "flex";
        return;
    }

    subjectEl.innerText = subjects[index].name;
    progressEl.innerText = `Subject ${index + 1} of ${subjects.length}`;

    const angle = (index / subjects.length) * 360;
    circle.style.background = `conic-gradient(#4f46e5 ${angle}deg, #1e293b ${angle}deg)`;

    marksInput.value = "";
    marksInput.focus();
}
