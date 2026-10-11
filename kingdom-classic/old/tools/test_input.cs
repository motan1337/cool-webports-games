using System;

public static class InputTests
{
    private static int assertions;
    private static void Check(bool value, string message)
    {
        assertions++;
        if (!value) throw new Exception(message);
    }

    public static void Main()
    {
        KingdomInputState s = new KingdomInputState();
        s.Advance(0, 1, 0, false, false, false, false, false, true);
        Check(s.GetAxisRaw(0) == 1 && s.GetButtonDown(0), "Right press enters movement");
        Check(!s.GetButtonDoublePressDown(0), "First right press is not a double press");
        s.Advance(0.1f, 0, 0, false, false, false, false, false, true);
        s.Advance(0.3f, 1, 0, false, false, false, false, false, true);
        Check(s.GetButtonDoublePressDown(0), "Second right press within recovered 0.6s window gallops");
        s.Advance(0.4f, -1, 0, true, true, false, false, false, true);
        Check(s.GetNegativeButtonDown(0), "Direction changes enter left movement");
        Check(!s.GetNegativeButtonDoublePressDown(0), "Right and left double-press histories remain independent");
        Check(s.GetButton(1) && s.GetButtonDown(1), "Pay hold and initial press are distinct");
        s.Advance(0.9f, -1, 0, true, true, false, false, false, true);
        Check(s.GetButtonTimePressed(1) > 0.49f, "Intro skip and payment hold timing advances");
        Check(!s.GetButtonDown(1), "Held payment does not repeat its press edge");
        s.Advance(1, -1, 0, true, true, false, false, false, false);
        Check(s.GetAxisRaw(0) == 0 && !s.GetButton(1), "Focus loss clears movement and payment");
        Check(s.GetButtonUp(2), "Focus loss releases gallop");
        s.Advance(1.1f, -1, 0, false, false, false, false, false, true);
        Check(!s.GetNegativeButtonDoublePressDown(0), "Regaining focus does not create a double press");
        s.Advance(2, 0, -1, false, false, true, true, false, true);
        Check(s.GetAxis(3) == -1 && s.GetButtonDown(4) && s.GetButtonDown(5), "Menu navigation, submit and pause are independent");
        s.Advance(3, 1, 0, false, false, false, false, false, true);
        s.Advance(3.2f, 1, 0, false, false, false, false, false, true);
        Check(s.GetAxisRawTimeActive(0) > 0.19f, "Intro movement duration uses real time");
        Console.WriteLine("Input checks passed: " + assertions);
    }
}
