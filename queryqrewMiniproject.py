import sqlite3
import sys
from datetime import date


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
    #users use this to log in to their existing profile
    email = input("Email: ")
    password = input("Password: ")

    #now, we check if email & password combo is in members(email, passwd)
    #our cursor now holds the count of instances where there is a match for email and password of users
    cursor.execute('''
                   SELECT count(*) FROM members WHERE email=? and passwd=?;
                   ''', (email, password))

    count = cursor.fetchone()[0]
    
    if count == 1:
        #this means the password and email acctually have an associated account!
        return email

    else:
        #this means the email/password are incorrect
        print("incorrect email/password, please try again.")
        return None

def register():
    #Users use this to make a new profile
    print("Please enter your details to register.")
    email = input("Email: ")
    # Check if the email already exists
    cursor.execute('''
		   SELECT count(*) FROM members WHERE email=?;
		   ''', (email))
    count = cursor.fetchone()[0]

    if count > 0:
        print("This email is already registered.")
        return None
    else:
        name = input("Name: ")
        byear = input("Birth Year: ")
        faculty = input("Faculty: ")
        password = input("Password: ")
        cursor.execute('''
            INSERT INTO members (email, passwd, name, byear, faculty) VALUES (?, ?, ?, ?, ?);
                       ''', (email, password, name, byear, faculty))
        
        connection.commit()
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
    print(f"Name: {info[0]}\nEmail: {info[1]}\nBirth Year: {info[2]}\nFaculty: {info[3]}")

def displayBorrowingInformation(email):
    cursor.execute('''
        SELECT COUNT(*),
               (SELECT COUNT(*) FROM borrowings WHERE member=? AND end_date IS NULL) AS current_borrowings,
               (SELECT COUNT(*) FROM borrowings WHERE member=? AND end_date IS NULL AND julianday('now') - julianday(start_date) > 20) AS overdue_borrowings
        FROM borrowings WHERE member=?;
    ''', (email, email, email)) #julianday is current day in SQLite
    info = cursor.fetchone()
    print("\nBorrowing Information:")
    print(f"Total books borrowed (including returned): {info[0]}")
    print(f"Current borrowings (unreturned books): {info[1]}")
    print(f"Overdue borrowings (not returned within the deadline): {info[2]}")

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
    #this function is for returning a book 
    #display current borrowings (list bid, book title, borrwing date, return_deadline) 
    cursor.execute('''
        SELECT bid, book_id, start_date, (start_date + 20) AS return_deadline
        FROM borrowings
        WHERE bid IN (SELECT bid FROM borrowings WHERE member=?);
    ''', (email))
    info = cursor.fetchall()
    
    for row in info:
        print("bid: ", row[0], " book id: ", row[1], " start date: ", row[2], " return deadline: ", row[3])
    
    #now that all info is printed, we can ask for a borrowing return
    bidToReturn = input("\nEnter a bid to return: ")
    for row in info:
        if row[0] == bidToReturn:
            returnBookByBid(bidToReturn, email)

    #if we are here, it means no valid bid was selected by the user
    print("Sorry, that is not a valid bid. please enter a valid bid to return a book.")
    returnBookMenu(email) #loop back to start of the function

def returnBookByBid(bid, email):
    #this is the function where the return will happen, given a specific bid
    cursor.execute('''
        SELECT bid, book_id, start_date, end_date, (start_date + 20) AS return_deadline
        FROM borrowings
        WHERE bid =?;
    ''', (bid))
    info = cursor.fetchone()


            #THIS PART MIGHT NEED CHANGING DEPENDING ON NESSISARY FORMAT FOR DATES!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    todayDate = str(date.today()) #MIGHT NEED TO CHANGE, CURRENTLY LIKE: 2024-03-13
    


    if info[3] == None: #this means that the book has not already been returned , so we need to add an end_date to the respective row
        cursor.execute('''
        UPDATE borrowings SET end_date =?
        WHERE bid =?;
        ''', (todayDate, bid))
            #THIS PART MIGHT NEED CHANGING DEPENDING ON NESSISARY FORMAT FOR DATES!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        daysDifference = (info[3]-info[2]).days()
        if daysDifference > 20: #The book was not returned on time
            daysLate = daysDifference - 20 #this becomes the penalty amount, like $daysLate

            pid = None #(generate a unique pid, do this by doing a query of penalties, sort by pid DESC, take the first one and add one to it)
            cursor.execute('''
            SELECT pid
            FROM penalties
            ORDER BY pid DESC LIMIT 1;
            ''')
            row = cursor.fetchone()
            pid = int(row[0]) + 1 #now our pid is unique!

            #insert a new penalty
            cursor.execute('''
            INSERT INTO penalties VALUES
            (?, ?, ?, ?);
            ''', (pid, bid, daysLate, 0))
            print("This is a late return, therfore a penalty has been added to your account. ")

        else: #the book was returned on time
            print("Thank you for returning this book on time!")
        

        reviewResponse = None
        while reviewResponse == None:
            reviewResponse = (input("Would you like to leave a review? Type y for yes, or n for no")).lower()
            if reviewResponse == "y":
                getReview(bid, email)
            elif reviewResponse == "n":
                mainMenu()
            else:
                print("Please enter a valid response")
                reviewResponse = None

    elif (info[3] != None) or (info[0] == None): #this means an invalid bid was entered
        print("Please enter a valid bid.")
        returnBookMenu() #re prints all the valid options, back to returnBookMenu


def getReview(bid, email):
    rating = int(input("Please enter a rating of 1-5: "))
    if (rating > 5) or (rating < 1):
        print("Please enter a valid rating.")
        getReview(bid, email)
    else: #for valid ratings
        
        rtext = input("Please enter the review text: ")
        
        rid = None #(generate a unique rid, do this by doing a query of reviews, sort by pid DESC, take the first one and add one to it)
        cursor.execute('''
        SELECT rid
        FROM reviews
        ORDER BY pid DESC LIMIT 1;
        ''')

        row = cursor.fetchone()
        rid = int(row[0]) + 1 #now our rid is unique!

        
        cursor.execute('''
        SELECT book_id
        FROM borrowings
        WHERE bid =?;
        ''', (bid))
        book_id = (cursor.fetchone())[0]

        todayDate = str(date.today()) #MIGHT NEED TO CHANGE, CURRENTLY LIKE: 2024-03-13

        #now we can add the new review into the reviews relation!
        connection.execute('''
        INSERT INTO reviews VALUES
        (?, ?, ?, ?);
        ''', (rid, book_id, email, rating, rtext, todayDate))
        connection.commit
        
        print("Thank you for the review!")
        mainMenu()

def searchForBooks():
    keyword = input("Enter a keyword to search for book/author: ").strip()
    offset = 0
    while True:
        # NOT SURE IF QUERY IS CORRECT!!!!!!
        cursor.execute('''
            SELECT b.book_id, b.title, b.author, b.pyear
            FROM books b
            WHERE b.title LIKE ? OR b.author LIKE ?
            ORDER BY b.title, b.author
            LIMIT 5 OFFSET ?;
        ''', ('%' + keyword + '%', '%' + keyword + '%', offset))

        books = cursor.fetchall()

        # If no books are found, it just exits the function
        if not books:
            print("No books found")
            return 

        for book in books:
            # Display book information here, if needed
            print("Book ID:", book[0])
            print("Title:", book[1])
            print("Author:", book[2])
            print("Publication Year:", book[3])
            print()

        # If less than 5 books are found, it's the end of the list
        if len(books) < 5:
            return 
        
        see_more = input("Would you like to see more books? (y/n): ").lower()
        if see_more != 'y':
            break 

        offset += 5

    # Borrowing functionality
    borrow = input("Would you like to borrow a book (y/n)? ").lower()
    if borrow == 'y':
        book_id_to_borrow = input("Enter book ID to borrow: ").strip()
        if book_id_to_borrow.isdigit():
            return borrowBook(int(book_id_to_borrow))

def borrowBook(book_id):
    cursor.execute('SELECT COUNT(*) FROM borrowings WHERE book_id = ? AND end_date IS NULL', (book_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute('INSERT INTO borrowings (member, book_id, start_date) VALUES (?, ?, DATE("now"))', (current_user_email, book_id))
        connection.commit()
        return "Book borrowed successfully."
    else:
        return "Book not available."

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
    
    # Ask user to select a penalty to pay
    selected_pid = input("Enter the Penalty ID you want to pay: ")
    selected_amount = None
    for penalty in penalties:
        if penalty[0] == selected_pid:
            selected_amount = penalty[1]
            break
    else:
        print("Invalid Penalty ID.")
        return
    
    # Ask user to enter payment amount
    payment_amount = float(input(f"Enter the payment amount for Penalty ID {selected_pid}: "))
    if payment_amount <= 0:
        print("Invalid payment amount.")
        return

    if payment_amount > selected_amount:
        print("Payment amount exceeds the penalty amount. Please enter a valid payment amount.")
        return
    
    # Update penalty payment

    new_paid_amount = penalty[2] + payment_amount

    cursor.execute('''
        UPDATE penalties SET paid_amount = ?
        WHERE pid = ?;
    ''', (new_paid_amount, selected_pid))

    connection.commit()

    print("Payment successful.")

def main():
    path = "./register.db"
    connect(path)
    try:
        startMenu()
    finally:
        connection.close()

if __name__ == "__main__":
    main()
