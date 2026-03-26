
// Toggles the hamburger menu with click

document.querySelector('.hamburger').addEventListener('click', function() {
    var navRight = document.getElementById('navbarRight');
    if (navRight.style.left === "0px") {
        navRight.style.left = "-100%"; // Slide out
    } else {
        navRight.style.left = "0"; // Slide in
    }
});

document.querySelector('.hamburger').addEventListener('click', function() {
    document.getElementById('navbarRight').style.left = "0"; // Slide in
});

document.querySelector('.closebtn').addEventListener('click', function() {
    document.getElementById('navbarRight').style.left = "-100%"; // Slide out
});




// Toggles the dropdown menu with click

const dropBtn = document.getElementById('dropBtn');
if (dropBtn) { // Check if the element actually exists
const dropdownContent = document.querySelector('.dropdown-content');

dropBtn.addEventListener('click', function() {
    console.log('clicked');
    if (dropdownContent.style.display === "none") {
        dropdownContent.style.display = "block";
    } else {
        dropdownContent.style.display = "none";
    }
    console.log(dropdownContent);
});
}



async function addNewUserToFirestore(user) {
  const userData = {
    created_at: new Date().toISOString().split('T')[0], // "YYYY-MM-DD"
    email: user.email,
    google_cal_name: "TennisBookingBot",
    autobook_enabled: false,
    google_calendar_connected: false,
    club_profile_connected: false,
    setup_complete: false,
    user_id: user.uid
  };
  // Use Firebase Auth UID as the document ID for uniqueness
  await setDoc(doc(db, "users", user.uid), userData);
}