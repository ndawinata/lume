const historyModal = document.getElementById("historyModal");
const historyIcon = document.getElementById("historyIcon");

// Get the close button inside the modal
const closeButton = historyModal.querySelector(".close");

// Function to open the modal
function openModal() {
    // historyModal.style.display = "block";
    historyModal.style.display = "flex";
    fetchData()
}

// Function to close the modal
function closeModal() {
    historyModal.style.display = "none";
}

// Event listener to open the modal when the history icon is clicked
historyIcon.addEventListener("click", openModal);

// Event listener to close the modal when the close button is clicked
closeButton.addEventListener("click", closeModal);

// Event listener to close the modal when clicking outside the modal content
window.addEventListener("click", (event) => {
    if (event.target === historyModal) {
        closeModal();
    }
});



