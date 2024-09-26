import sqlite3
import sys
from datetime import date
from datetime import datetime
import getpass

connection = None
cursor = None
current_user_email = None #global var to keep email

#the connext function was taken from the lab sample code provided on eclass from the week 6 section,
#... and is being used to connect our program to the needed database
def connect(path): 
    global connection, cursor

    connection = sqlite3.connect(path)
    cursor = connection.cursor()
    cursor.execute(' PRAGMA foreign_keys=ON; ')
    connection.commit()
    return

def startMenu():
    #this function prints out all of the options open to the user after starting the program
    print("Welcome to system")
    status = (input("Are you registered or unregistered? Enter r for registered, or anything else for unregistered: ")).lower()
    if status == "r":
        #go to login sequence
        email = login()
    else:
        #go to register sequence
        email = register()
    if email:
        current_user_email = email
        mainMenu()
    else:
        print("Failed to log in or register.")
        startMenu()

def login():
    global current_user_email  # Add this line
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    cursor.execute('SELECT count(*) FROM members WHERE email=? AND passwd=?;', (email, password))
    count = cursor.fetchone()[0]
    
    if count == 1:
        current_user_email = email  # This updates the global variable
        return email
    else:
        print("Incorrect email/password, please try again.")
        return None

def register():
    global current_user_email  # Add this line
    print("Please enter your details to register.")
    email = input("Email: ")
    cursor.execute('SELECT count(*) FROM members WHERE email=?;', (email,))
    count = cursor.fetchone()[0]

    if count > 0:
        print("This email is already registered.")
        return None
    else:
        name = input("Name: ")
        byear = input("Birth Year: ")
        faculty = input("Faculty: ")
        password = getpass.getpass("Password: ")
        cursor.execute('INSERT INTO members (email, passwd, name, byear, faculty) VALUES (?, ?, ?, ?, ?);', 
                       (email, password, name, byear, faculty))
        connection.commit()
        current_user_email = email  # Update the global variable after successful registration
        print("Registration successful!")
        return email
    
def mainMenu():
    #this function prints out all of the options open to the user after logging in
    global current_user_email
    print("~=~ MAIN MENU ~=~")
    print("Enter a number to pick an option:")
    print("1 - Log Out")
    print("2 - Exit Program")
    print("3 - Member Profile")
    print("4 - Return a Book")
    print("5 - Search for a Book")
    print("6 - Pay a Penalty")

    menuInput = input("\nPlease select an option: ")
    try:
        menuInput = int(menuInput)
    except ValueError:
        print("Invalid input. Please enter a number.")
        mainMenu()
        return

                #1 - Log Out
    if menuInput == 1:
        current_user_email = None
        startMenu()
    
                #2 - Exit program
    elif menuInput == 2:
        sys.exit("Thank you for using the system. Goodbye!") 

                #3 - Memeber Profile
    elif menuInput == 3:
        memberProfile(current_user_email)

                #4 - Return a book
    elif menuInput == 4:
        returnBookMenu(current_user_email)

                #5 - Search for a book
    elif menuInput == 5:
        searchForBooks()

                #6 - Pay a penalty
    elif menuInput == 6:
        payPenalty(current_user_email)
    
    else:
        print("Invalid option.")
        mainMenu()

def memberProfile(email):
    while True:
        print("\n~=~ Member Profile Menu ~=~")
        print("1 - View Personal Information")
        print("2 - View Borrowing Information")
        print("3 - View Penalty Information")
        print("4 - Return to Main Menu")
        profileInput = input("Select an option: ")

        if profileInput == '1':
            displayPersonalInformation(email)
        elif profileInput == '2':
            displayBorrowingInformation(email)
        elif profileInput == '3':
            displayPenaltyInformation(email)
        elif profileInput == '4':
            break
        else:
            print("Invalid option, please try again.")

    mainMenu()  # Return to the main menu after exiting the submenu

def displayPersonalInformation(email):
    cursor.execute('''
                   SELECT name, email, byear, faculty FROM members WHERE email=?;
                   ''', (email,))
    info = cursor.fetchone()
    print("\nPersonal Information:")
    print(f"Name: {info[0]}\nEmail: {info[1]}\nBirth Year: {info[2]}\nFaculty: {info[3]}\n")

def displayBorrowingInformation(email):
    cursor.execute('''
        SELECT COUNT(*),
               (SELECT COUNT(*) FROM borrowings WHERE member=? AND end_date IS NULL) AS current_borrowings
        FROM borrowings WHERE member=?;
    ''', (email, email))

    total_borrowings, current_borrowings = cursor.fetchone()

    # this query calculates overdue borrowings (without julianday;-;)
    cursor.execute('''
        SELECT COUNT(*) FROM borrowings
        WHERE member=? AND end_date IS NULL
        AND DATE('now') > DATE(start_date, '+20 days');
    ''', (email,))
    overdue_borrowings = cursor.fetchone()[0]

    print("\nBorrowing Information:")
    print(f"Total books borrowed (including returned): {total_borrowings}")
    print(f"Current borrowings (unreturned books): {current_borrowings}")
    print(f"Overdue borrowings (not returned within the deadline): {overdue_borrowings}")

def displayPenaltyInformation(email):
    cursor.execute('''
        SELECT COUNT(*), SUM(amount - paid_amount) AS total_unpaid
        FROM penalties
        WHERE bid IN (SELECT bid FROM borrowings WHERE member=?) AND amount > paid_amount;
    ''', (email,))
    info = cursor.fetchone()
    unpaid_count = info[0]
    total_unpaid = info[1] if info[1] else 0 # accounts for cases with no unpaid debt
    print("\nPenalty Information:")
    print(f"Number of unpaid penalties: {unpaid_count}")
    print(f"Total debt amount on unpaid penalties: {total_unpaid}")

def returnBookMenu(email):
    print("Current Borrowings:")
    cursor.execute('''
        SELECT bid, book_id, start_date, 
        strftime('%Y-%m-%d', start_date, '+20 days') AS return_deadline
        FROM borrowings
        WHERE member = ? AND end_date IS NULL;
    ''', (email,))
    borrowings= cursor.fetchall()

    if not borrowings:
        print("No current borrowings.")
        print()
        mainMenu()

    for borrowing in borrowings:
        print(f"bid: {borrowing[0]}, book id: {borrowing[1]}, start date: {borrowing[2]}, return deadline: {borrowing[3]}")

    bidToReturn = input("\nEnter a bid to return: ")
    if any(str(borrowing[0]) == bidToReturn for borrowing in borrowings):
        returnBookByBid(bidToReturn, email)
    else:
        print("Sorry, but you have entered an invalid bid. Please enter a valid bid to return a book.")
        returnBookMenu(email)

def returnBookByBid(bid, email):
    cursor.execute('''
        SELECT start_date FROM borrowings WHERE bid = ? AND member = ? AND end_date IS NULL;
    ''', (bid, email))
    borrowing = cursor.fetchone()

    if borrowing:
        todayDate = date.today().isoformat()
        cursor.execute('''
            SELECT julianday(?) - julianday(start_date) AS days_passed FROM borrowings WHERE bid = ?;
        ''', (todayDate, bid))
        days_passed = cursor.fetchone()[0]

        cursor.execute('''
            UPDATE borrowings SET end_date = ? WHERE bid = ?;
        ''', (todayDate, bid))

        if days_passed > 20:
            days_late = days_passed - 20
            cursor.execute('''
                INSERT INTO penalties (bid, amount, paid_amount) VALUES (?, ?, 0);
            ''', (bid, days_late))
            print(f"Return processed. Late return penalty applied for {int(days_late)} days overdue.")
        else:
            print("Return has been processed, thank you for returning the book on time.")

        # Prompt for a review after return
        review_choice = input("Would you like to leave a review? (y/n): ").lower()
        if review_choice == 'y':
            getReview(bid, email)

        connection.commit()
    else:
        print("Invalid borrowing ID or the book does not belong to the current user.")
    mainMenu()
def getReview(bid, email):
    cursor.execute("SELECT book_id FROM borrowings WHERE bid = ?", (bid,))
    result = cursor.fetchone()
    if result is None:
        print("Error: No borrowing found for the given BID.")
        return
    book_id = result[0]

    cursor.execute("SELECT * FROM books WHERE book_id = ?", (book_id,))
    if cursor.fetchone() is None:
        print(f"Error: No book found with book_id: {book_id}")
        return

    # Collecting review details from user
    try:
        rating = int(input("Please enter a rating of 1-5: "))
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5.")
    except ValueError as e:
        print(e)
        return

    rtext = input("Please enter the review text: ")
    todayDate = date.today().strftime('%Y-%m-%d')

    cursor.execute("SELECT MAX(rid) FROM reviews")
    max_rid = cursor.fetchone()[0]
    rid = 1 if max_rid is None else max_rid + 1

    cursor.execute('''INSERT INTO reviews (rid, book_id, member, rating, rtext, rdate)
                      VALUES (?, ?, ?, ?, ?, ?);''', (rid, book_id, email, rating, rtext, todayDate))
    connection.commit()
    print("Review added successfully.")
   
    mainMenu()


def searchForBooks():
    keyword = input("Enter a keyword to search for book/author: ").strip()
    page_size = 5
    offset = 0

    while True:
        cursor.execute('''
            SELECT b.book_id, b.title, b.author, b.pyear
            FROM books b
            WHERE b.title LIKE ? OR b.author LIKE ?
            ORDER BY b.title, b.author
            LIMIT ? OFFSET ?;
        ''', ('%' + keyword + '%', '%' + keyword + '%', page_size, offset))

        books = cursor.fetchall()

        if not books:
            if offset == 0:
                print("No books found matching your query.")
            else:
                print("No more books found.")
            break

        for book in books:
            print(f"Book ID: {book[0]}\nTitle: {book[1]}\nAuthor: {book[2]}\nPublication Year: {book[3]}")
            print()

        while True:
            if offset == 0:
                user_input = input("Enter 'n' for next page, 'e' to exit, or a book ID to borrow: ").lower()
            else:
                user_input = input("Enter 'n' for next page, 'p' for previous page, 'e' to exit, or a book ID to borrow: ").lower()

            if user_input == 'n':
                offset += page_size
                break
            elif user_input == 'p' and offset >= page_size:
                offset -= page_size
                break
            elif user_input.isdigit():
                borrowBook(int(user_input))
                return  # Directly returns after borrowing, simplifying the flow
            elif user_input == 'e':
                return  # Exit search
            else:
                print("Invalid input, please try again.")

    mainMenu()  # Returns to the main menu after the search is complete or a book is borrowed

def borrowBook(book_id):
    global current_user_email  # Ensure this is declared globally if you haven't already
    if not current_user_email:
        print("You must be logged in to borrow a book.")
        return

    cursor.execute('SELECT COUNT(*) FROM borrowings WHERE book_id = ? AND end_date IS NULL', (book_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        print("This book is currently borrowed.")
        return

    cursor.execute('INSERT INTO borrowings (member, book_id, start_date) VALUES (?, ?, DATE("now"))', (current_user_email, book_id))
    connection.commit()
    print("You have successfully borrowed the book.")

    mainMenu()
def payPenalty(email):
    
    # Find unpaid penalties
    cursor.execute('''
        SELECT pid, amount, paid_amount
        FROM penalties
        WHERE bid IN (SELECT bid FROM borrowings WHERE member=?) AND amount > paid_amount;
    ''', (email,))

    penalties = cursor.fetchall()

    if not penalties:
        print("No unpaid penalties.")
        return

    # Display unpaid penalties
    print("Unpaid Penalties:")
    for penalty in penalties:
        pid, amount, paid_amount = penalty
        print(f"Penalty ID: {pid}, Amount: {amount}, Paid Amount: {paid_amount}")
    
    while True:
        # Ask user to select a penalty to pay
        selected_pid = input("Enter the Penalty ID you want to pay or 'exit' to return: ")
        if selected_pid.lower() == 'exit':
            break

        selected_pid = int(selected_pid) if selected_pid.isdigit() else None
        selected_penalty = next((p for p in penalties if p[0] == selected_pid), None)

        if selected_penalty:
            # if the correct penalty is selected, we proceed with payment process
            pid, amount, paid_amount = selected_penalty
            try:
                payment_amount = float(input(f"Enter the payment amount for Penalty ID {selected_pid} (Remaining Amount: {amount - paid_amount}): "))
                if payment_amount <= 0 or payment_amount + paid_amount > amount:
                    raise ValueError("Invalid payment amount.")

                new_paid_amount = paid_amount + payment_amount

                cursor.execute('UPDATE penalties SET paid_amount = ? WHERE pid = ?', (new_paid_amount, pid))
                connection.commit()

                print("Payment successful. Thank you.")
                break
            except ValueError as e:
                print(e)
        else:
            print("Invalid Penalty ID. Please try again.")
    mainMenu()

def main():
    if len(sys.argv) < 2:
        print("Usage: python script_name.py database_path")
        sys.exit(1)  # Exit the script with an error status

    path = sys.argv[1]  # Read the database path from command line arguments
    connect(path)
    try:
        startMenu()
    finally:
        connection.close()

if __name__ == "__main__":
    main()
