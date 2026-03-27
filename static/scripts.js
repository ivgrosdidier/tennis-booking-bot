
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

