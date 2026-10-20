// RideGo Application Scripts

document.addEventListener("DOMContentLoaded", () => {
    // Auto-dismiss Django messages after 4 seconds
    const messages = document.querySelectorAll(".message");
    if (messages.length > 0) {
        setTimeout(() => {
            messages.forEach((msg) => {
                msg.style.transition = "opacity 0.6s ease, transform 0.6s ease";
                msg.style.opacity = "0";
                msg.style.transform = "translateY(-10px)";
                setTimeout(() => msg.remove(), 600);
            });
        }, 4000);
    }
});

function copyCoupon() {
    if (navigator.clipboard) {
        navigator.clipboard.writeText("RAPID20").then(() => {
            alert("🎉 Coupon code RAPID20 copied to clipboard! Enjoy 20% OFF your ride.");
        }).catch(() => {
            alert("Coupon code: RAPID20");
        });
    } else {
        alert("Coupon code: RAPID20");
    }
}