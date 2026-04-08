console.log("Scripts loaded");

// Example: Highlight active page link
document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll(".dashboard a");
    links.forEach(link => {
        if(link.href === window.location.href){
            link.style.backgroundColor = "#ffce00";
        }
    });
});