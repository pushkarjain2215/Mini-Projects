// // function transformData(data) {
// //     const { analytics, studentInfo } = data;
// //     const { semesterWise, cgpa } = analytics;

// //     const semesters = {};
// //     const allSubjects = [];

// //     let overallTotalMarks = 0;
// //     let overallMaxMarks = 0;
// //     let overallTotalCredits = 0;
// //     let overallTotalCreditPoints = 0;
// //     let overallCreditMarks = 0;
// //     let overallMaxCreditMarks = 0;

// //     for (const sem in semesterWise) {
// //         const semester = semesterWise[sem];
// //         semesters[sem] = {
// //             subjects: semester.subjects,
// //             totalMarks: semester.subjects.reduce((acc, sub) => acc + sub.marks, 0),
// //             maxMarks: semester.subjects.length * 100,
// //             totalCredits: semester.totalCredits,
// //             totalCreditPoints: semester.totalCreditPoints,
// //             creditMarks: semester.subjects.reduce((acc, sub) => acc + (sub.marks * sub.credits), 0),
// //             maxCreditMarks: semester.subjects.reduce((acc, sub) => acc + (100 * sub.credits), 0),
// //             sgpa: semester.sgpa,
// //             percentage: 0,
// //             creditPercentage: 0,
// //         };

// //         semesters[sem].percentage = (semesters[sem].totalMarks / semesters[sem].maxMarks) * 100;
// //         semesters[sem].creditPercentage = (semesters[sem].creditMarks / semesters[sem].maxCreditMarks) * 100;

// //         allSubjects.push(...semester.subjects);

// //         overallTotalMarks += semesters[sem].totalMarks;
// //         overallMaxMarks += semesters[sem].maxMarks;
// //         overallTotalCredits += semesters[sem].totalCredits;
// //         overallTotalCreditPoints += semesters[sem].totalCreditPoints;
// //         overallCreditMarks += semesters[sem].creditMarks;
// //         overallMaxCreditMarks += semesters[sem].maxCreditMarks;
// //     }

// //     const overall = {
// //         marks: `${overallTotalMarks} / ${overallMaxMarks}`,
// //         percentage: `${((overallTotalMarks / overallMaxMarks) * 100).toFixed(3)} %`,
// //         creditMarks: `${overallCreditMarks} / ${overallMaxCreditMarks}`,
// //         creditPercentage: `${((overallCreditMarks / overallMaxCreditMarks) * 100).toFixed(3)} %`,
// //         cgpa: cgpa.toFixed(3),
// //         equivalentPercentage: `${(cgpa * 10).toFixed(3)} %`,
// //         creditsObtained: `${overallTotalCredits} / ${overallTotalCredits}`,
// //     };

// //     const yearWise = {};
// //     for (let i = 1; i <= Math.ceil(Object.keys(semesters).length / 2); i++) {
// //         const sem1 = (i * 2) - 1;
// //         const sem2 = i * 2;

// //         yearWise[i] = {
// //             totalMarks: 0,
// //             maxMarks: 0,
// //             totalCredits: 0,
// //             totalCreditPoints: 0,
// //             gpa: 0,
// //             percentage: 0,
// //         };

// //         if (semesters[sem1]) {
// //             yearWise[i].totalMarks += semesters[sem1].totalMarks;
// //             yearWise[i].maxMarks += semesters[sem1].maxMarks;
// //             yearWise[i].totalCredits += semesters[sem1].totalCredits;
// //             yearWise[i].totalCreditPoints += semesters[sem1].totalCreditPoints;
// //         }
// //         if (semesters[sem2]) {
// //             yearWise[i].totalMarks += semesters[sem2].totalMarks;
// //             yearWise[i].maxMarks += semesters[sem2].maxMarks;
// //             yearWise[i].totalCredits += semesters[sem2].totalCredits;
// //             yearWise[i].totalCreditPoints += semesters[sem2].totalCreditPoints;
// //         }

// //         yearWise[i].gpa = (yearWise[i].totalCreditPoints / yearWise[i].totalCredits);
// //         yearWise[i].percentage = (yearWise[i].totalMarks / yearWise[i].maxMarks) * 100;
// //     }

// //     const cumulativeSemester = {};
// //     let cumulativeMarks = 0;
// //     let cumulativeMaxMarks = 0;
// //     let cumulativeCredits = 0;
// //     let cumulativeCreditPoints = 0;
// //     for (const sem in semesters) {
// //         cumulativeMarks += semesters[sem].totalMarks;
// //         cumulativeMaxMarks += semesters[sem].maxMarks;
// //         cumulativeCredits += semesters[sem].totalCredits;
// //         cumulativeCreditPoints += semesters[sem].totalCreditPoints;
// //         cumulativeSemester[sem] = {
// //             marks: `${cumulativeMarks}/${cumulativeMaxMarks}`,
// //             percentage: `${((cumulativeMarks/cumulativeMaxMarks)*100).toFixed(2)}%`,
// //             gpa: (cumulativeCreditPoints/cumulativeCredits).toFixed(2),
// //         }
// //     }

// //     const cumulativeYear = {};
// //     let cumulativeYearMarks = 0;
// //     let cumulativeYearMaxMarks = 0;
// //     let cumulativeYearCredits = 0;
// //     let cumulativeYearCreditPoints = 0;
// //     for (let i = 1; i <= Math.ceil(Object.keys(semesters).length / 2); i++) {
// //         cumulativeYearMarks += yearWise[i].totalMarks;
// //         cumulativeYearMaxMarks += yearWise[i].maxMarks;
// //         cumulativeYearCredits += yearWise[i].totalCredits;
// //         cumulativeYearCreditPoints += yearWise[i].totalCreditPoints;
// //         cumulativeYear[i] = {
// //             marks: `${cumulativeYearMarks}/${cumulativeYearMaxMarks}`,
// //             percentage: `${((cumulativeYearMarks/cumulativeYearMaxMarks)*100).toFixed(2)}%`,
// //             gpa: (cumulativeYearCreditPoints/cumulativeYearCredits).toFixed(2),
// //         }
// //     }

// //     console.log("Original analytics from backend:", analytics); // Log original analytics
// //     console.log("Transformed semesters data:", semesters); // Log transformed semesters data

// //     return {
// //         studentInfo,
// //         overall,
// //         semesters,
// //         allSubjects,
// //         yearWise,
// //         cumulativeSemester,
// //         cumulativeYear,
// //     };
// // }

// function transformData(data) {
//     const { analytics, studentInfo } = data;
//     const { semesterWise, cgpa } = analytics;

//     const semesters = {};
//     const allSubjects = [];

//     let overallTotalMarks = 0;
//     let overallMaxMarks = 0;
//     let overallTotalCredits = 0;
//     let overallTotalCreditPoints = 0;
//     let overallCreditMarks = 0;
//     let overallMaxCreditMarks = 0;

//     for (const sem in semesterWise) {
//         const semester = semesterWise[sem];

//         // Map subjects to ensure they have all required fields
//         const mappedSubjects = semester.subjects.map((subject) => ({
//             paperCode: subject.paperCode || "N/A",
//             subjectName: subject.subjectName || "N/A",
//             internal: subject.internal || "0",
//             external: subject.external || "0",
//             total: subject.total || subject.marks || "0",
//             marks: subject.marks || subject.total || 0,
//             credits: subject.credits || 0,
//             grade: subject.grade || "N/A",
//             exam: subject.exam || "N/A",
//             declaredDate: subject.declaredDate || "N/A",
//         }));

//         semesters[sem] = {
//             subjects: mappedSubjects,
//             totalMarks: mappedSubjects.reduce((acc, sub) => {
//                 const marks = parseFloat(sub.marks) || 0;
//                 return acc + marks;
//             }, 0),
//             maxMarks: mappedSubjects.length * 100,
//             totalCredits: semester.totalCredits || 0,
//             totalCreditPoints: semester.totalCreditPoints || 0,
//             creditMarks: mappedSubjects.reduce((acc, sub) => {
//                 const marks = parseFloat(sub.marks) || 0;
//                 const credits = parseFloat(sub.credits) || 0;
//                 return acc + marks * credits;
//             }, 0),
//             maxCreditMarks: mappedSubjects.reduce((acc, sub) => {
//                 const credits = parseFloat(sub.credits) || 0;
//                 return acc + 100 * credits;
//             }, 0),
//             sgpa: semester.sgpa || 0,
//             percentage: 0,
//             creditPercentage: 0,
//         };

//         // Calculate percentages
//         if (semesters[sem].maxMarks > 0) {
//             semesters[sem].percentage =
//                 (semesters[sem].totalMarks / semesters[sem].maxMarks) * 100;
//         }

//         if (semesters[sem].maxCreditMarks > 0) {
//             semesters[sem].creditPercentage =
//                 (semesters[sem].creditMarks / semesters[sem].maxCreditMarks) *
//                 100;
//         }

//         allSubjects.push(...mappedSubjects);

//         overallTotalMarks += semesters[sem].totalMarks;
//         overallMaxMarks += semesters[sem].maxMarks;
//         overallTotalCredits += semesters[sem].totalCredits;
//         overallTotalCreditPoints += semesters[sem].totalCreditPoints;
//         overallCreditMarks += semesters[sem].creditMarks;
//         overallMaxCreditMarks += semesters[sem].maxCreditMarks;
//     }

//     const overall = {
//         marks: `${overallTotalMarks.toFixed(0)} / ${overallMaxMarks}`,
//         percentage: `${((overallTotalMarks / overallMaxMarks) * 100).toFixed(3)} %`,
//         creditMarks: `${overallCreditMarks.toFixed(0)} / ${overallMaxCreditMarks}`,
//         creditPercentage: `${((overallCreditMarks / overallMaxCreditMarks) * 100).toFixed(3)} %`,
//         cgpa: cgpa.toFixed(3),
//         equivalentPercentage: `${(cgpa * 10).toFixed(3)} %`,
//         creditsObtained: `${overallTotalCredits} / ${overallTotalCredits}`,
//     };

//     const yearWise = {};
//     for (let i = 1; i <= Math.ceil(Object.keys(semesters).length / 2); i++) {
//         const sem1 = i * 2 - 1;
//         const sem2 = i * 2;

//         yearWise[i] = {
//             totalMarks: 0,
//             maxMarks: 0,
//             totalCredits: 0,
//             totalCreditPoints: 0,
//             gpa: 0,
//             percentage: 0,
//         };

//         if (semesters[sem1]) {
//             yearWise[i].totalMarks += semesters[sem1].totalMarks;
//             yearWise[i].maxMarks += semesters[sem1].maxMarks;
//             yearWise[i].totalCredits += semesters[sem1].totalCredits;
//             yearWise[i].totalCreditPoints += semesters[sem1].totalCreditPoints;
//         }
//         if (semesters[sem2]) {
//             yearWise[i].totalMarks += semesters[sem2].totalMarks;
//             yearWise[i].maxMarks += semesters[sem2].maxMarks;
//             yearWise[i].totalCredits += semesters[sem2].totalCredits;
//             yearWise[i].totalCreditPoints += semesters[sem2].totalCreditPoints;
//         }

//         if (yearWise[i].totalCredits > 0) {
//             yearWise[i].gpa =
//                 yearWise[i].totalCreditPoints / yearWise[i].totalCredits;
//         }

//         if (yearWise[i].maxMarks > 0) {
//             yearWise[i].percentage =
//                 (yearWise[i].totalMarks / yearWise[i].maxMarks) * 100;
//         }
//     }

//     const cumulativeSemester = {};
//     let cumulativeMarks = 0;
//     let cumulativeMaxMarks = 0;
//     let cumulativeCredits = 0;
//     let cumulativeCreditPoints = 0;
//     for (const sem in semesters) {
//         cumulativeMarks += semesters[sem].totalMarks;
//         cumulativeMaxMarks += semesters[sem].maxMarks;
//         cumulativeCredits += semesters[sem].totalCredits;
//         cumulativeCreditPoints += semesters[sem].totalCreditPoints;
//         cumulativeSemester[sem] = {
//             marks: `${cumulativeMarks.toFixed(0)}/${cumulativeMaxMarks}`,
//             percentage:
//                 cumulativeMaxMarks > 0
//                     ? `${((cumulativeMarks / cumulativeMaxMarks) * 100).toFixed(2)}%`
//                     : "0.00%",
//             gpa:
//                 cumulativeCredits > 0
//                     ? (cumulativeCreditPoints / cumulativeCredits).toFixed(2)
//                     : "0.00",
//         };
//     }

//     const cumulativeYear = {};
//     let cumulativeYearMarks = 0;
//     let cumulativeYearMaxMarks = 0;
//     let cumulativeYearCredits = 0;
//     let cumulativeYearCreditPoints = 0;
//     for (let i = 1; i <= Math.ceil(Object.keys(semesters).length / 2); i++) {
//         cumulativeYearMarks += yearWise[i].totalMarks;
//         cumulativeYearMaxMarks += yearWise[i].maxMarks;
//         cumulativeYearCredits += yearWise[i].totalCredits;
//         cumulativeYearCreditPoints += yearWise[i].totalCreditPoints;
//         cumulativeYear[i] = {
//             marks: `${cumulativeYearMarks.toFixed(0)}/${cumulativeYearMaxMarks}`,
//             percentage:
//                 cumulativeYearMaxMarks > 0
//                     ? `${((cumulativeYearMarks / cumulativeYearMaxMarks) * 100).toFixed(2)}%`
//                     : "0.00%",
//             gpa:
//                 cumulativeYearCredits > 0
//                     ? (
//                           cumulativeYearCreditPoints / cumulativeYearCredits
//                       ).toFixed(2)
//                     : "0.00",
//         };
//     }

//     console.log("Original analytics from backend:", analytics);
//     console.log("Transformed semesters data:", semesters);
//     console.log("Sample subject from semester 1:", semesters[1]?.subjects[0]);

//     return {
//         studentInfo,
//         overall,
//         semesters,
//         allSubjects,
//         yearWise,
//         cumulativeSemester,
//         cumulativeYear,
//     };
// }

function transformData(data) {
    const { analytics, studentInfo } = data;
    const { semesterWise, cgpa } = analytics;

    const semesters = {};
    const allSubjects = [];

    let overallTotalMarks = 0;
    let overallMaxMarks = 0;
    let overallTotalCredits = 0;
    let overallTotalCreditPoints = 0;
    let overallCreditMarks = 0;
    let overallMaxCreditMarks = 0;

    for (const sem in semesterWise) {
        const semester = semesterWise[sem];
        
        // Map subjects and ensure all fields are properly set
        const mappedSubjects = semester.subjects.map(subject => {
            // Preserve original string values for internal/external/paperCode
            // Only parse if we need numeric calculations
            const internalStr = (subject.internal && subject.internal.trim() !== '') ? subject.internal.trim() : '0';
            const externalStr = (subject.external && subject.external.trim() !== '') ? subject.external.trim() : '0';
            const paperCodeStr = (subject.paperCode && subject.paperCode.trim() !== '') ? subject.paperCode.trim() : 'N/A';
            
            // Parse numeric values for calculations
            const internal = parseFloat(internalStr) || 0;
            const external = parseFloat(externalStr) || 0;
            const total = parseFloat(subject.total) || parseFloat(subject.marks) || (internal + external);
            const marks = parseFloat(subject.marks) || total;
            const credits = parseFloat(subject.credits) || 0;
            
            return {
                paperCode: paperCodeStr,
                subjectName: (subject.subjectName && subject.subjectName.trim() !== '') ? subject.subjectName.trim() : 'N/A',
                internal: internalStr,
                external: externalStr,
                total: total.toString(),
                marks: marks,
                credits: credits,
                grade: (subject.grade && subject.grade.trim() !== '') ? subject.grade.trim() : 'N/A',
                exam: (subject.exam && subject.exam.trim() !== '') ? subject.exam.trim() : 'N/A',
                declaredDate: (subject.declaredDate && subject.declaredDate.trim() !== '') ? subject.declaredDate.trim() : 'N/A'
            };
        });
        
        console.log(`Semester ${sem} mapped subjects:`, mappedSubjects);
        
        semesters[sem] = {
            subjects: mappedSubjects,
            totalMarks: mappedSubjects.reduce((acc, sub) => acc + sub.marks, 0),
            maxMarks: mappedSubjects.length * 100,
            totalCredits: semester.totalCredits || 0,
            totalCreditPoints: semester.totalCreditPoints || 0,
            creditMarks: mappedSubjects.reduce((acc, sub) => acc + (sub.marks * sub.credits), 0),
            maxCreditMarks: mappedSubjects.reduce((acc, sub) => acc + (100 * sub.credits), 0),
            sgpa: semester.sgpa || 0,
            percentage: 0,
            creditPercentage: 0,
        };

        // Calculate percentages safely
        if (semesters[sem].maxMarks > 0) {
            semesters[sem].percentage = (semesters[sem].totalMarks / semesters[sem].maxMarks) * 100;
        }
        
        if (semesters[sem].maxCreditMarks > 0) {
            semesters[sem].creditPercentage = (semesters[sem].creditMarks / semesters[sem].maxCreditMarks) * 100;
        }
        
        allSubjects.push(...mappedSubjects);

        overallTotalMarks += semesters[sem].totalMarks;
        overallMaxMarks += semesters[sem].maxMarks;
        overallTotalCredits += semesters[sem].totalCredits;
        overallTotalCreditPoints += semesters[sem].totalCreditPoints;
        overallCreditMarks += semesters[sem].creditMarks;
        overallMaxCreditMarks += semesters[sem].maxCreditMarks;
    }

    const overall = {
        marks: `${overallTotalMarks.toFixed(0)} / ${overallMaxMarks}`,
        percentage: overallMaxMarks > 0 ? `${((overallTotalMarks / overallMaxMarks) * 100).toFixed(3)} %` : '0.000 %',
        creditMarks: `${overallCreditMarks.toFixed(0)} / ${overallMaxCreditMarks}`,
        creditPercentage: overallMaxCreditMarks > 0 ? `${((overallCreditMarks / overallMaxCreditMarks) * 100).toFixed(3)} %` : '0.000 %',
        cgpa: cgpa.toFixed(3),
        equivalentPercentage: `${(cgpa * 10).toFixed(3)} %`,
        creditsObtained: `${overallTotalCredits} / ${overallTotalCredits}`,
    };
    
    const yearWise = {};
    for (let i = 1; i <= Math.ceil(Object.keys(semesters).length / 2); i++) {
        const sem1 = (i * 2) - 1;
        const sem2 = i * 2;
        
        yearWise[i] = {
            totalMarks: 0,
            maxMarks: 0,
            totalCredits: 0,
            totalCreditPoints: 0,
            gpa: 0,
            percentage: 0,
        };

        if (semesters[sem1]) {
            yearWise[i].totalMarks += semesters[sem1].totalMarks;
            yearWise[i].maxMarks += semesters[sem1].maxMarks;
            yearWise[i].totalCredits += semesters[sem1].totalCredits;
            yearWise[i].totalCreditPoints += semesters[sem1].totalCreditPoints;
        }
        if (semesters[sem2]) {
            yearWise[i].totalMarks += semesters[sem2].totalMarks;
            yearWise[i].maxMarks += semesters[sem2].maxMarks;
            yearWise[i].totalCredits += semesters[sem2].totalCredits;
            yearWise[i].totalCreditPoints += semesters[sem2].totalCreditPoints;
        }

        if (yearWise[i].totalCredits > 0) {
            yearWise[i].gpa = (yearWise[i].totalCreditPoints / yearWise[i].totalCredits);
        }
        
        if (yearWise[i].maxMarks > 0) {
            yearWise[i].percentage = (yearWise[i].totalMarks / yearWise[i].maxMarks) * 100;
        }
    }

    const cumulativeSemester = {};
    let cumulativeMarks = 0;
    let cumulativeMaxMarks = 0;
    let cumulativeCredits = 0;
    let cumulativeCreditPoints = 0;
    for (const sem in semesters) {
        cumulativeMarks += semesters[sem].totalMarks;
        cumulativeMaxMarks += semesters[sem].maxMarks;
        cumulativeCredits += semesters[sem].totalCredits;
        cumulativeCreditPoints += semesters[sem].totalCreditPoints;
        cumulativeSemester[sem] = {
            marks: `${cumulativeMarks.toFixed(0)}/${cumulativeMaxMarks}`,
            percentage: cumulativeMaxMarks > 0 ? `${((cumulativeMarks/cumulativeMaxMarks)*100).toFixed(2)}%` : '0.00%',
            gpa: cumulativeCredits > 0 ? (cumulativeCreditPoints/cumulativeCredits).toFixed(2) : '0.00',
        }
    }
    
    const cumulativeYear = {};
    let cumulativeYearMarks = 0;
    let cumulativeYearMaxMarks = 0;
    let cumulativeYearCredits = 0;
    let cumulativeYearCreditPoints = 0;
    for (let i = 1; i <= Math.ceil(Object.keys(semesters).length / 2); i++) {
        cumulativeYearMarks += yearWise[i].totalMarks;
        cumulativeYearMaxMarks += yearWise[i].maxMarks;
        cumulativeYearCredits += yearWise[i].totalCredits;
        cumulativeYearCreditPoints += yearWise[i].totalCreditPoints;
        cumulativeYear[i] = {
            marks: `${cumulativeYearMarks.toFixed(0)}/${cumulativeYearMaxMarks}`,
            percentage: cumulativeYearMaxMarks > 0 ? `${((cumulativeYearMarks/cumulativeYearMaxMarks)*100).toFixed(2)}%` : '0.00%',
            gpa: cumulativeYearCredits > 0 ? (cumulativeYearCreditPoints/cumulativeYearCredits).toFixed(2) : '0.00',
        }
    }

    console.log("Original analytics from backend:", analytics);
    console.log("Transformed semesters data:", semesters);
    console.log("Sample subject from first available semester:", Object.values(semesters)[0]?.subjects[0]);

    return {
        studentInfo,
        overall,
        semesters,
        allSubjects,
        yearWise,
        cumulativeSemester,
        cumulativeYear,
    };
}