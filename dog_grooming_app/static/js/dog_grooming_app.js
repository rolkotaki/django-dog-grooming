
/**
 * Sets today's date by default to query free booking slots, on the Admin page.
 * Also sets the min and max value of the date input.
 */
function setInitialDateForAvailableBookingSlotsOnAdminPage() {
    document.getElementById("date").min = new Date().toISOString().split("T")[0];
    document.getElementById("date").value = new Date().toISOString().split("T")[0];
    max_date = new Date()
    max_date.setDate(max_date.getDate() + 90)
    document.getElementById("date").max = max_date.toISOString().split("T")[0];
}

/**
 * Sets the href value of the link button to update or delete a specific service, on the Admin page.
 */
function setServiceUpdateDeleteAPIUrlOnAdminPage(element) {
    var serviceUpdateDeleteButton = document.getElementById("service_update_delete_button");
    if (element.value != "none") {
        serviceUpdateDeleteButton.href = "api/admin/service/update_delete/" + element.value + "/";
    } else {
        serviceUpdateDeleteButton.href = "";
    }
}

/**
 * Sets the href value of the link button to get the free booking slots for a specific service, on the Admin page.
 */
function setAvailableBookingSlotsAPIUrlOnAdminPage() {
    var listFreeBookingSlotsButton = document.getElementById("free_booking_slots_button");
    var dateInput = document.getElementById("date");
    var serviceInput = document.getElementById("service_list");
    if (serviceInput.value != "none") {
        listFreeBookingSlotsButton.href = "api/booking/free_booking_slots?day=" + dateInput.value + "&service_id=" + serviceInput.value;
    } else {
        listFreeBookingSlotsButton.href = "";
    }
}

/**
 * Sets the gallery image deletion button enabled or disabled based on if there is an image selected, on the Admin page.
 */
function enableDisableGalleryImageDeleteButtonOnAdminPage(element) {
    var deleteButton = document.getElementById("image_delete_button");
    if (element.value != "none") {
        deleteButton.disabled = false;
    } else {
        deleteButton.disabled = true;
    }
}

/**
 * Sets the href value of the link button to cancel a user, on the Admin page.
 */
function setCancelUserAPIUrlOnAdminPage(element) {
    var cancelUserButton = document.getElementById("cancel_user_button");
    if (element.value != "none") {
        cancelUserButton.href = "api/admin/user/" + element.value + "/cancel";
    } else {
        cancelUserButton.href = "";
    }
}

/**
 * Displays and enlarges an image in the gallery page.
 */
function displayGalleryImage(img) {
    var expandedImage = document.getElementById("expanded_image");
    expandedImage.src = img.src;
    expandedImage.parentElement.parentElement.parentElement.style.display = "grid";
}

/**
 * Sets tomorrow's date by default as the value of the date input on the booking page.
 * Also sets the min and max value of the date input.
 */
function setInitialDateOnBookingPage() {
    min_date = new Date()
    min_date.setDate(min_date.getDate() + 1)
    max_date = new Date()
    max_date.setDate(max_date.getDate() + 90)
    document.getElementById("date").min = min_date.toISOString().split("T")[0];
    document.getElementById("date").value = min_date.toISOString().split("T")[0];
    document.getElementById("date").max = max_date.toISOString().split("T")[0];
}

/**
 * Displays the booking price corresponding to the dog size.
 */
function changeBookingPriceForDogSize(element) {
    var value = element.value
    document.getElementById("small").style.display = "none";
    document.getElementById("medium").style.display = "none";
    document.getElementById("big").style.display = "none";
    document.getElementById(value).style.display = "block";
}

/**
 * Fetches the available booking time slots for the specific date that the user selects from the date input,
 * on the booking page. Having fetched the available booking slots, it updates the option child elements
 * of the select element containing the available booking slots.
 */
function fetchAvailableBookingTimeSlots() {
    $.ajax({
        url: '/api/booking/free_booking_slots',
        type: 'GET',
        data: {day: $('#date').val(), service_id: $('#service_id').val()},
        success: function(response) {
            $('#time').children().remove();
            for (const bookingTimeSlot of response.booking_slots) {
                const option = document.createElement('option');
                option.value = bookingTimeSlot[0];
                option.textContent = bookingTimeSlot[1];
                $('#time').append(option);
            }
        },
        error: function(error) {
            console.error('Error fetching the booking time slots:', error);
        }
    });
}
