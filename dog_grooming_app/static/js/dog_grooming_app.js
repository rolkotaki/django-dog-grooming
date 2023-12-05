
/**
 * Sets the style of the active navigation menu item to active.
 */
$(document).ready(function() {
    $('#topnav a').click(function(e) {
        $('#topnav a').removeClass('active_menu');
        $('#topnav button').removeClass('active_menu');
        if (['nav_personal_data', 'nav_user_bookings', 'nav_admin_bookings'].includes($(this).attr('id'))) {
            sessionStorage.setItem('active_menu', 'user_dropdown_button');
        } else {
            sessionStorage.setItem('active_menu', $(this).attr('id'));
        }
    });
    const activeMenuId = sessionStorage.getItem('active_menu');
    $('#' + activeMenuId).addClass('active_menu');
});

/**
 * Sets today's date by default to query available booking slots, on the Admin page.
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
    let serviceUpdateDeleteButton = document.getElementById("service_update_delete_button");
    if (element.value != "none") {
        serviceUpdateDeleteButton.href = "api/admin/service/update_delete/" + element.value + "/";
    } else {
        serviceUpdateDeleteButton.href = "";
    }
}

/**
 * Sets the href value of the link button to get the available booking slots for a specific service, on the Admin page.
 */
function setAvailableBookingSlotsAPIUrlOnAdminPage() {
    let listAvailableBookingSlotsButton = document.getElementById("available_booking_slots_button");
    const dateInput = document.getElementById("date");
    const serviceInput = document.getElementById("service_list");
    if (serviceInput.value != "none") {
        listAvailableBookingSlotsButton.href = "api/booking/available_booking_slots?day=" + dateInput.value + "&service_id=" + serviceInput.value;
    } else {
        listAvailableBookingSlotsButton.href = "";
    }
}

/**
 * Sets the gallery image deletion button enabled or disabled based on if there is an image selected, on the Admin page.
 */
function enableDisableGalleryImageDeleteButtonOnAdminPage(element) {
    let deleteButton = document.getElementById("image_delete_button");
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
    let cancelUserButton = document.getElementById("cancel_user_button");
    if (element.value != "none") {
        cancelUserButton.href = "api/admin/user/" + element.value + "/cancel";
    } else {
        cancelUserButton.href = "";
    }
}

/**
 * Sets the href value of the link button to view the services, on the Admin page.
 */
function setListServicesAPIUrlOnAdminPage(element) {
    const href = "api/admin/services"
    let link_params = ""
    let viewServicesButton = document.getElementById("view_services_button");
    const radioButtons = document.querySelectorAll('input[name="rg_service_filter"]');

    for (const radioButton of radioButtons) {
        if (radioButton.checked) {
            if (radioButton.value == "active") {
                link_params = "?active=true";
            } else if (radioButton.value == "inactive") {
                link_params = "?active=false";
            }
            break;
        }
    }
    viewServicesButton.href = href + link_params;
}

/**
 * Sets the href value of the link button to view the bookings, on the Admin page.
 */
function setListBookingsAPIUrlOnAdminPage(element) {
    const href = "api/admin/bookings"
    let link_params = ""
    let viewBookingsButton = document.getElementById("view_bookings_button");
    const cbActiveBooking = document.getElementById("cb_active_booking");
    const radioButtons = document.querySelectorAll('input[name="rg_booking_filter"]');

    if (cbActiveBooking.checked) {
        link_params += "&active=false";
    } else {
        link_params += "&active=true";
    }
    for (const radioButton of radioButtons) {
        if (radioButton.checked) {
            if (radioButton.value == "active") {
                link_params += "&cancelled=false";
            } else if (radioButton.value == "cancelled") {
                link_params += "&cancelled=true";
            }
            break;
        }
    }
    viewBookingsButton.href = href + "?" + link_params.substring(1);
}

/**
 * Sets the href value of the link button to view the users, on the Admin page.
 */
function setListUsersAPIUrlOnAdminPage(element) {
    const href = "api/admin/users"
    let link_params = ""
    let viewUsersButton = document.getElementById("view_users_button");
    const radioButtons = document.querySelectorAll('input[name="rg_user_filter"]');

    for (const radioButton of radioButtons) {
        if (radioButton.checked) {
            if (radioButton.value == "active") {
                link_params = "?active=true";
            } else if (radioButton.value == "inactive") {
                link_params = "?active=false";
            }
            break;
        }
    }
    viewUsersButton.href = href + link_params;
}

/**
 * Displays and enlarges an image in the gallery page.
 */
function displayGalleryImage(img) {
    let expandedImage = document.getElementById("expanded_image");
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
    const value = element.value
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
        url: '/api/booking/available_booking_slots',
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
