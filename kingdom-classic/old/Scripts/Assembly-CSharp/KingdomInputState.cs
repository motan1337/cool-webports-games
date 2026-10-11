using System;

public sealed class KingdomInputState
{
    public const float DoublePressWindow = 0.6f;
    private readonly bool[] held = new bool[11];
    private readonly bool[] down = new bool[11];
    private readonly bool[] up = new bool[11];
    private readonly float[] pressedAt = new float[11];
    private float lastRight = float.NegativeInfinity;
    private float lastLeft = float.NegativeInfinity;
    private float horizontalStarted;
    private float now;
    private int horizontal;
    private int vertical;
    private bool leftHeld;
    private bool leftDown;
    private bool rightDouble;
    private bool leftDouble;

    public void Advance(float time, int move, int menuMove, bool pay, bool gallop,
                        bool submit, bool pause, bool debug, bool focused)
    {
        now = time;
        if (!focused)
        {
            move = menuMove = 0;
            pay = gallop = submit = pause = debug = false;
            lastRight = lastLeft = float.NegativeInfinity;
        }
        bool previousLeft = leftHeld;
        leftHeld = move < 0;
        leftDown = leftHeld && !previousLeft;
        bool rightDown = move > 0 && !held[0];
        rightDouble = rightDown && time - lastRight <= DoublePressWindow;
        leftDouble = leftDown && time - lastLeft <= DoublePressWindow;
        if (rightDown) lastRight = time;
        if (leftDown) lastLeft = time;
        if (horizontal == 0 && move != 0) horizontalStarted = time;
        horizontal = move;
        vertical = menuMove;
        Set(0, move > 0);
        Set(1, pay);
        Set(2, gallop);
        Set(3, menuMove > 0);
        Set(4, submit);
        Set(5, pause);
        Set(6, pause);
        Set(10, debug);
    }

    private void Set(int id, bool value)
    {
        down[id] = value && !held[id];
        up[id] = !value && held[id];
        if (down[id]) pressedAt[id] = now;
        held[id] = value;
    }

    public float GetAxisRaw(int id) { return id == 0 ? horizontal : id == 3 ? vertical : 0; }
    public float GetAxis(int id) { return GetAxisRaw(id); }
    public bool GetButton(int id) { return id >= 0 && id < held.Length && held[id]; }
    public bool GetButtonDown(int id) { return id >= 0 && id < down.Length && down[id]; }
    public bool GetButtonUp(int id) { return id >= 0 && id < up.Length && up[id]; }
    public bool GetNegativeButtonDown(int id) { return id == 0 && leftDown; }
    public bool GetButtonDoublePressDown(int id) { return id == 0 && rightDouble; }
    public bool GetNegativeButtonDoublePressDown(int id) { return id == 0 && leftDouble; }
    public float GetButtonTimePressed(int id) { return GetButton(id) ? now - pressedAt[id] : 0; }
    public float GetAxisRawTimeActive(int id) { return id == 0 && horizontal != 0 ? now - horizontalStarted : 0; }
}
